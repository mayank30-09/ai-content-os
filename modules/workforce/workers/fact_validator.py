"""Fact validator for Fact Checker Worker subsystem.

Validates extracted factual claims against ResearchPackage and ContextPackage
evidence using a pluggable matching strategy pattern.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from loguru import logger

from modules.memory.models import ContextPackage
from modules.research.models import ResearchPackage
from modules.workforce.workers.claim_extractor import ExtractedClaim
from modules.workforce.workers.verification_models import (
    ClaimResult,
    IssueSeverity,
    VerificationStatus,
)

# Common English stop words excluded from Jaccard token matching
_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "are", "was", "were",
    "be", "been", "has", "have", "had", "do", "does", "did", "not",
    "it", "its", "this", "that", "these", "those", "as", "if",
})

# ---------------------------------------------------------------------------
# Pluggable Matching Strategy Interface
# ---------------------------------------------------------------------------

class MatchingStrategy(ABC):
    """Abstract interface for claim-to-source matching strategies.

    Concrete strategies implement ``match`` to compute a confidence score and
    source reference for a given claim against a body of source text.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable strategy identifier."""
        ...

    @abstractmethod
    def match(self, claim_text: str, source_texts: list[str]) -> tuple[float, str | None]:
        """Evaluates how well a claim text is supported by source texts.

        Args:
            claim_text: The extracted claim text to verify.
            source_texts: List of source document content strings.

        Returns:
            Tuple of:
            - confidence: float in [0.0, 1.0].
            - matched_text: Best-matching excerpt from sources, or None.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete Strategy: Jaccard Token Overlap
# ---------------------------------------------------------------------------

class JaccardOverlapStrategy(MatchingStrategy):
    """Jaccard token overlap matching strategy.

    Computes the Jaccard similarity coefficient between the claim token set
    and each source document's token set, returning the maximum score.
    """

    @property
    def strategy_name(self) -> str:
        """Strategy identifier."""
        return "jaccard_overlap"

    def match(self, claim_text: str, source_texts: list[str]) -> tuple[float, str | None]:
        """Computes maximum Jaccard overlap between claim and source documents.

        Args:
            claim_text: Claim text to verify.
            source_texts: Source text bodies.

        Returns:
            Tuple of (best_confidence, best_matched_excerpt).
        """
        if not source_texts:
            return 0.0, None

        claim_tokens = self._tokenize(claim_text)
        if not claim_tokens:
            return 0.0, None

        best_score = 0.0
        best_excerpt: str | None = None

        for source in source_texts:
            if not source:
                continue
            score, excerpt = self._score_against_source(claim_tokens, source)
            if score > best_score:
                best_score = score
                best_excerpt = excerpt

        return round(best_score, 3), best_excerpt

    def _score_against_source(self, claim_tokens: set[str], source: str) -> tuple[float, str | None]:
        """Slides a window over the source text to find the best-matching segment.

        Args:
            claim_tokens: Tokenized claim word set.
            source: Source document content.

        Returns:
            Tuple of (jaccard_score, matching_excerpt).
        """
        words = re.findall(r"\b\w+\b", source.lower())
        if not words:
            return 0.0, None

        window_size = max(len(claim_tokens) * 2, 20)
        best_score = 0.0
        best_start = 0

        for i in range(max(1, len(words) - window_size + 1)):
            window_tokens = set(words[i : i + window_size])
            intersection = claim_tokens & window_tokens
            union = claim_tokens | window_tokens
            score = len(intersection) / len(union) if union else 0.0
            if score > best_score:
                best_score = score
                best_start = i

        if best_score > 0:
            excerpt_words = words[best_start : best_start + window_size]
            excerpt = " ".join(excerpt_words[:25]) + ("..." if len(excerpt_words) > 25 else "")
        else:
            excerpt = None

        return best_score, excerpt

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenizes text into lowercase word set, removing stop words."""
        tokens = re.findall(r"\b\w{3,}\b", text.lower())
        return {t for t in tokens if t not in _STOP_WORDS}


# ---------------------------------------------------------------------------
# Concrete Strategy: Substring Inclusion
# ---------------------------------------------------------------------------

class SubstringInclusionStrategy(MatchingStrategy):
    """Substring-based matching strategy.

    Returns a high confidence score when key terms from the claim appear
    verbatim as substrings within source documents.
    """

    @property
    def strategy_name(self) -> str:
        """Strategy identifier."""
        return "substring_inclusion"

    def match(self, claim_text: str, source_texts: list[str]) -> tuple[float, str | None]:
        """Checks if claim keywords appear as substrings in any source.

        Args:
            claim_text: Claim text to verify.
            source_texts: Source text bodies.

        Returns:
            Tuple of (confidence, matched_excerpt).
        """
        claim_lower = claim_text.lower()
        keywords = [w for w in re.findall(r"\b\w{5,}\b", claim_lower) if len(w) >= 5]
        if not keywords:
            return 0.0, None

        for source in source_texts:
            if not source:
                continue
            source_lower = source.lower()
            matched = sum(1 for kw in keywords if kw in source_lower)
            if matched >= max(1, len(keywords) // 2):
                # Find excerpt around first matching keyword
                first_kw = next((kw for kw in keywords if kw in source_lower), None)
                excerpt = None
                if first_kw:
                    idx = source_lower.index(first_kw)
                    start = max(0, idx - 50)
                    end = min(len(source), idx + 80)
                    excerpt = source[start:end].strip()
                confidence = min(1.0, matched / len(keywords))
                return round(confidence, 3), excerpt

        return 0.0, None


# ---------------------------------------------------------------------------
# FactValidator
# ---------------------------------------------------------------------------

class FactValidator:
    """Validates extracted claims against research and context evidence.

    Supports pluggable matching strategies. By default, uses
    ``JaccardOverlapStrategy`` as the primary matcher and falls back to
    ``SubstringInclusionStrategy`` when the primary confidence is low.

    Args:
        primary_strategy: Primary MatchingStrategy instance.
        fallback_strategy: Optional fallback strategy when primary score is
            below ``fallback_threshold``.
        fallback_threshold: Confidence floor below which fallback is attempted.
        verified_threshold: Minimum confidence to classify a claim as VERIFIED.
        partial_threshold: Minimum confidence for PARTIALLY_VERIFIED status.
        hallucination_threshold: Maximum allowed confidence before a claim
            is escalated to HALLUCINATION_SUSPECTED (only for CONTRADICTED detection).
    """

    def __init__(
        self,
        primary_strategy: MatchingStrategy | None = None,
        fallback_strategy: MatchingStrategy | None = None,
        fallback_threshold: float = 0.25,
        verified_threshold: float = 0.45,
        partial_threshold: float = 0.20,
    ) -> None:
        self._primary: MatchingStrategy = primary_strategy or JaccardOverlapStrategy()
        self._fallback: MatchingStrategy | None = fallback_strategy or SubstringInclusionStrategy()
        self._fallback_threshold = fallback_threshold
        self._verified_threshold = verified_threshold
        self._partial_threshold = partial_threshold

    def validate_claims(
        self,
        claims: list[ExtractedClaim],
        research_package: ResearchPackage | None,
        context_package: ContextPackage | None,
    ) -> list[ClaimResult]:
        """Validates each extracted claim against available source evidence.

        Args:
            claims: Extracted claims from ClaimExtractor.
            research_package: ResearchPackage source evidence.
            context_package: ContextPackage memory evidence.

        Returns:
            List of ClaimResult models for each claim.
        """
        source_texts = self._build_source_corpus(research_package, context_package)

        results: list[ClaimResult] = []
        for claim in claims:
            result = self._validate_single_claim(claim, source_texts)
            results.append(result)

        verified = sum(1 for r in results if r.status in {VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED})
        logger.info(
            f"FactValidator validated {len(claims)} claims: "
            f"{verified} supported, "
            f"{sum(1 for r in results if r.status == VerificationStatus.UNVERIFIED)} unsupported, "
            f"{sum(1 for r in results if r.status == VerificationStatus.HALLUCINATION_SUSPECTED)} suspected hallucinations."
        )
        return results

    def _validate_single_claim(
        self,
        claim: ExtractedClaim,
        source_texts: list[str],
    ) -> ClaimResult:
        """Validates a single ExtractedClaim against the source corpus.

        Args:
            claim: The claim to validate.
            source_texts: Compiled source text strings.

        Returns:
            ClaimResult with status, confidence, and matched excerpt.
        """
        if not source_texts:
            return ClaimResult(
                claim_text=claim.text,
                category=claim.category,
                status=VerificationStatus.UNVERIFIED,
                verification_method=self._primary.strategy_name,
                issue_severity=IssueSeverity.MEDIUM,
                confidence=0.0,
            )

        # Primary strategy
        confidence, matched_text = self._primary.match(claim.text, source_texts)
        method = self._primary.strategy_name

        # Fallback strategy when primary score is weak
        if confidence < self._fallback_threshold and self._fallback:
            fb_confidence, fb_matched = self._fallback.match(claim.text, source_texts)
            if fb_confidence > confidence:
                confidence = fb_confidence
                matched_text = fb_matched
                method = self._fallback.strategy_name

        status, severity = self._classify_claim(confidence)

        return ClaimResult(
            claim_text=claim.text,
            category=claim.category,
            status=status,
            matched_text=matched_text,
            verification_method=method,
            issue_severity=severity,
            confidence=confidence,
        )

    def _classify_claim(self, confidence: float) -> tuple[VerificationStatus, IssueSeverity]:
        """Maps a confidence score to a VerificationStatus and IssueSeverity.

        Args:
            confidence: Confidence score in [0.0, 1.0].

        Returns:
            Tuple of (VerificationStatus, IssueSeverity).
        """
        if confidence >= self._verified_threshold:
            return VerificationStatus.VERIFIED, IssueSeverity.INFO
        if confidence >= self._partial_threshold:
            return VerificationStatus.PARTIALLY_VERIFIED, IssueSeverity.LOW
        if confidence > 0.05:
            return VerificationStatus.UNVERIFIED, IssueSeverity.MEDIUM
        # Near-zero confidence with no source match: suspect hallucination
        return VerificationStatus.HALLUCINATION_SUSPECTED, IssueSeverity.HIGH

    @staticmethod
    def _build_source_corpus(
        research_package: ResearchPackage | None,
        context_package: ContextPackage | None,
    ) -> list[str]:
        """Aggregates all available source text into a flat corpus list.

        Args:
            research_package: Research package containing ranked documents.
            context_package: Context package containing memory records.

        Returns:
            List of non-empty source text strings.
        """
        texts: list[str] = []

        if research_package:
            if research_package.executive_summary:
                texts.append(research_package.executive_summary)
            texts.extend(research_package.key_facts)
            for doc in research_package.ranked_documents:
                if doc.content:
                    texts.append(doc.content)
                if doc.summary:
                    texts.append(doc.summary)

        if context_package:
            for mem in context_package.research_memories:
                if mem.content:
                    texts.append(mem.content)
                texts.extend(mem.key_facts)
            for mem in context_package.knowledge_memories:
                if mem.content:
                    texts.append(mem.content)
                texts.extend(mem.claims)

        return [t for t in texts if t and t.strip()]
