"""Edit validator for Editor Worker subsystem.

Performs deterministic post-edit validation to verify that citations
and SEO keywords are preserved, and estimates readability and grammar
improvement between original and edited drafts.
"""

import re

from loguru import logger

from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.verification_models import VerifiedDraftPackage


class EditValidator:
    """Deterministic post-edit quality validator.

    Validates that the edited draft preserves citations and SEO keywords
    from the original, and estimates readability and grammar improvement
    using sentence-level heuristics. No LLM calls are made.

    This validator is stateless — each ``validate_edit`` call produces
    a fresh result from the provided inputs.
    """

    def validate_edit(
        self,
        original_draft: str,
        edited_draft: str,
        verified_pkg: VerifiedDraftPackage,
    ) -> tuple[EditQualityScores, list[str]]:
        """Validates the edited draft against the original and verified package.

        Args:
            original_draft: Original markdown draft from DraftPackage.
            edited_draft: Edited markdown draft from AI provider.
            verified_pkg: VerifiedDraftPackage containing citations and keywords.

        Returns:
            Tuple of:
            - EditQualityScores with all sub-scores computed.
            - List of issue description strings.
        """
        issues: list[str] = []

        citation_score = self._check_citation_preservation(
            verified_pkg.draft_package.citations_used, edited_draft, issues
        )
        keyword_score = self._check_keyword_preservation(
            verified_pkg.draft_package.seo_keywords, edited_draft, issues
        )
        readability_score = self._estimate_readability(edited_draft)
        grammar_score = self._estimate_grammar_improvement(original_draft, edited_draft)
        style_score = self._estimate_style_score(edited_draft)

        overall = round(
            (readability_score * 0.25)
            + (grammar_score * 0.20)
            + (style_score * 0.15)
            + (citation_score * 0.25)
            + (keyword_score * 0.15),
            3,
        )

        scores = EditQualityScores(
            readability_score=readability_score,
            grammar_score=grammar_score,
            style_score=style_score,
            citation_preservation_score=citation_score,
            keyword_preservation_score=keyword_score,
            overall_quality=overall,
        )

        logger.info(
            f"EditValidator: readability={readability_score:.2f}, grammar={grammar_score:.2f}, "
            f"style={style_score:.2f}, citation_pres={citation_score:.2f}, "
            f"keyword_pres={keyword_score:.2f}, overall={overall:.2f}, issues={len(issues)}"
        )
        return scores, issues

    def _check_citation_preservation(
        self,
        citations: list[dict],
        edited_draft: str,
        issues: list[str],
    ) -> float:
        """Checks that all citation URLs appear in the edited draft.

        Args:
            citations: Citation dicts from DraftPackage.citations_used.
            edited_draft: Edited markdown content.
            issues: Mutable issues list to append findings.

        Returns:
            Citation preservation ratio (0.0–1.0).
        """
        if not citations:
            return 1.0

        total = len(citations)
        preserved = 0
        edited_lower = edited_draft.lower()

        for c in citations:
            url = c.get("url", "")
            if url and url.lower() in edited_lower:
                preserved += 1
            elif url:
                issues.append(f"Citation URL missing from edited draft: {url}")

        score = round(preserved / total, 3) if total > 0 else 1.0
        return score

    def _check_keyword_preservation(
        self,
        keywords: list[str],
        edited_draft: str,
        issues: list[str],
    ) -> float:
        """Checks that SEO keywords appear in the edited draft.

        Args:
            keywords: SEO keywords from DraftPackage.seo_keywords.
            edited_draft: Edited markdown content.
            issues: Mutable issues list to append findings.

        Returns:
            Keyword preservation ratio (0.0–1.0).
        """
        if not keywords:
            return 1.0

        total = len(keywords)
        preserved = 0
        edited_lower = edited_draft.lower()

        for kw in keywords:
            if kw.lower() in edited_lower:
                preserved += 1
            else:
                issues.append(f"SEO keyword missing from edited draft: {kw}")

        score = round(preserved / total, 3) if total > 0 else 1.0
        return score

    def _estimate_readability(self, text: str) -> float:
        """Estimates readability using a sentence-length-based heuristic.

        Shorter average sentence lengths produce higher readability scores.
        Optimal average sentence length is considered 15–20 words.

        Args:
            text: Text to evaluate.

        Returns:
            Readability score (0.0–1.0).
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return 0.5

        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)

        # Optimal range: 12–22 words per sentence
        if 12 <= avg_length <= 22:
            return 1.0
        elif avg_length < 12:
            # Too short — slightly penalize
            return max(0.5, 1.0 - (12 - avg_length) * 0.05)
        else:
            # Too long — penalize more
            return max(0.3, 1.0 - (avg_length - 22) * 0.03)

    def _estimate_grammar_improvement(self, original: str, edited: str) -> float:
        """Estimates grammar improvement by comparing structural metrics.

        Compares sentence count variation and average sentence length
        convergence toward optimal range between original and edited.

        Args:
            original: Original draft text.
            edited: Edited draft text.

        Returns:
            Grammar quality score (0.0–1.0).
        """
        orig_sentences = self._split_sentences(original)
        edit_sentences = self._split_sentences(edited)

        if not orig_sentences or not edit_sentences:
            return 0.5

        orig_avg = sum(len(s.split()) for s in orig_sentences) / len(orig_sentences)
        edit_avg = sum(len(s.split()) for s in edit_sentences) / len(edit_sentences)

        # Score based on how close the edited average is to optimal (17 words)
        optimal = 17.0
        orig_dist = abs(orig_avg - optimal)
        edit_dist = abs(edit_avg - optimal)

        if edit_dist <= orig_dist:
            # Improved or maintained
            improvement_ratio = 1.0 - (edit_dist / max(optimal, 1.0))
            return round(max(0.5, min(1.0, improvement_ratio)), 3)
        else:
            # Worsened slightly
            return round(max(0.4, 1.0 - (edit_dist / max(optimal, 1.0))), 3)

    def _estimate_style_score(self, text: str) -> float:
        """Estimates style quality using paragraph and heading structure analysis.

        Evaluates whether the text has proper paragraph breaks, heading usage,
        and avoids excessively long unbroken text blocks.

        Args:
            text: Text to evaluate.

        Returns:
            Style score (0.0–1.0).
        """
        if not text or not text.strip():
            return 0.5

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        has_headings = bool(re.search(r"^#{1,6}\s", text, re.MULTILINE))

        score = 0.7  # Base score

        if has_headings:
            score += 0.15

        if len(paragraphs) >= 3:
            score += 0.10

        # Penalize very long paragraphs (> 200 words)
        long_paragraphs = sum(1 for p in paragraphs if len(p.split()) > 200)
        if long_paragraphs > 0:
            score -= 0.10 * min(long_paragraphs, 3)

        return round(max(0.3, min(1.0, score)), 3)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Splits text into sentences using punctuation boundaries.

        Args:
            text: Text to split.

        Returns:
            List of non-empty sentence strings.
        """
        raw = re.split(r"[.!?]+", text)
        return [s.strip() for s in raw if s.strip() and len(s.strip().split()) >= 3]
