"""Claim extractor for Fact Checker Worker subsystem.

Extracts factual claims, statistics, dates, quotations, and URLs
from markdown draft content using deterministic regex-based parsing.
"""

import re
from dataclasses import dataclass

from loguru import logger

# ---------------------------------------------------------------------------
# Extracted claim data container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractedClaim:
    """Immutable container for a single extracted factual claim.

    Attributes:
        text: Raw claim text snippet.
        category: Claim type identifier.
        position: Character offset of match in source draft.
    """

    text: str
    category: str
    position: int = 0


# ---------------------------------------------------------------------------
# Compiled regex patterns (module-level to avoid re-compilation per call)
# ---------------------------------------------------------------------------

_STATISTIC_PATTERN = re.compile(
    r"""
    (?:                          # open alternatives
      \d{1,3}(?:,\d{3})*        # integer with optional thousands separator
      (?:\.\d+)?                 # optional decimal part
      \s*%                       # percentage sign
    |
      \$\s*\d{1,3}(?:,\d{3})*  # currency: $1,200
      (?:\.\d+)?
      (?:\s*[KMBT](?:illion|rillion)?)?  # optional K/M/B/T scale
    |
      \d+(?:\.\d+)?              # plain number
      \s*(?:x|X|times)          # multiplier (10x, 3 times)
    |
      \d+(?:\.\d+)?              # number
      \s*(?:million|billion|trillion|thousand)  # long-form scale
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"""
    (?:
      \b(?:January|February|March|April|May|June|July|August|
           September|October|November|December)
      \s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b  # January 1st, 2024
    |
      \b\d{1,2}/\d{1,2}/\d{2,4}\b              # 01/01/2024
    |
      \b\d{4}-\d{2}-\d{2}\b                    # 2024-01-01 (ISO)
    |
      \bin\s+(?:19|20)\d{2}\b                   # in 2023
    |
      \bQ[1-4]\s+(?:20|19)\d{2}\b              # Q1 2024
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_QUOTE_PATTERN = re.compile(
    r"""
    (?:
      "([^"]{10,300})"          # double-quoted text (10–300 chars)
    |
      \u2018([^\u2019]{10,300})\u2019  # left/right single quotes
    |
      \u201c([^\u201d]{10,300})\u201d  # left/right double quotes
    )
    """,
    re.VERBOSE,
)

_URL_PATTERN = re.compile(
    r"https?://[^\s\]\)\"'<>]{5,}",
    re.IGNORECASE,
)

# General declarative sentence heuristic: "X is/are/was/were Y" constructs
# or sentences containing verbs of attribution.
_GENERAL_CLAIM_PATTERN = re.compile(
    r"""
    (?:
      [A-Z][^.!?\n]{20,150}    # sentence starting with capital letter
      (?:is|are|was|were|has|have|will|can|should|must|shows?|proves?|found|confirmed)
      [^.!?\n]{5,100}
      [.!?]
    )
    """,
    re.VERBOSE,
)


class ClaimExtractor:
    """Deterministic claim extractor for factual verification pipelines.

    Extracts five claim categories from markdown draft text:
    - ``statistic``: Numerical claims, percentages, and monetary figures.
    - ``date``: Temporal references including dates and year mentions.
    - ``quote``: Quoted text attributed to an author or source.
    - ``url``: Hyperlink references embedded in draft text.
    - ``general_fact``: Declarative factual assertions.

    This extractor is intentionally stateless — each ``extract_claims`` call
    produces a fresh result set from the provided draft text.
    """

    def extract_claims(self, draft: str) -> list[ExtractedClaim]:
        """Extracts all recognizable factual claims from a markdown draft.

        Args:
            draft: Raw markdown body content from a DraftPackage.

        Returns:
            List of ExtractedClaim instances in extraction order.
        """
        if not draft or not draft.strip():
            logger.debug("ClaimExtractor received empty or whitespace-only draft.")
            return []

        claims: list[ExtractedClaim] = []
        seen_texts: set[str] = set()

        claims.extend(self._extract_statistics(draft, seen_texts))
        claims.extend(self._extract_dates(draft, seen_texts))
        claims.extend(self._extract_quotes(draft, seen_texts))
        claims.extend(self._extract_urls(draft, seen_texts))
        claims.extend(self._extract_general_facts(draft, seen_texts))

        logger.debug(
            f"ClaimExtractor extracted {len(claims)} claims "
            f"({sum(1 for c in claims if c.category == 'statistic')} statistics, "
            f"{sum(1 for c in claims if c.category == 'date')} dates, "
            f"{sum(1 for c in claims if c.category == 'quote')} quotes, "
            f"{sum(1 for c in claims if c.category == 'url')} urls, "
            f"{sum(1 for c in claims if c.category == 'general_fact')} general_facts)."
        )
        return claims

    # ------------------------------------------------------------------
    # Private extraction helpers
    # ------------------------------------------------------------------

    def _extract_statistics(self, draft: str, seen: set[str]) -> list[ExtractedClaim]:
        """Extracts numerical statistics and monetary figures."""
        results: list[ExtractedClaim] = []
        for match in _STATISTIC_PATTERN.finditer(draft):
            # Include surrounding context (up to 80 chars) for verifiability
            start = max(0, match.start() - 40)
            end = min(len(draft), match.end() + 40)
            context_text = draft[start:end].strip()
            if context_text and context_text not in seen:
                seen.add(context_text)
                results.append(ExtractedClaim(text=context_text, category="statistic", position=match.start()))
        return results

    def _extract_dates(self, draft: str, seen: set[str]) -> list[ExtractedClaim]:
        """Extracts date and temporal references."""
        results: list[ExtractedClaim] = []
        for match in _DATE_PATTERN.finditer(draft):
            start = max(0, match.start() - 40)
            end = min(len(draft), match.end() + 40)
            context_text = draft[start:end].strip()
            if context_text and context_text not in seen:
                seen.add(context_text)
                results.append(ExtractedClaim(text=context_text, category="date", position=match.start()))
        return results

    def _extract_quotes(self, draft: str, seen: set[str]) -> list[ExtractedClaim]:
        """Extracts quoted text of at least 10 characters."""
        results: list[ExtractedClaim] = []
        for match in _QUOTE_PATTERN.finditer(draft):
            # Capture the non-None group
            text = next((g for g in match.groups() if g is not None), match.group()).strip()
            if text and text not in seen:
                seen.add(text)
                results.append(ExtractedClaim(text=text, category="quote", position=match.start()))
        return results

    def _extract_urls(self, draft: str, seen: set[str]) -> list[ExtractedClaim]:
        """Extracts raw HTTP/HTTPS URLs embedded in draft text."""
        results: list[ExtractedClaim] = []
        for match in _URL_PATTERN.finditer(draft):
            text = match.group().strip().rstrip(".,)")
            if text and text not in seen:
                seen.add(text)
                results.append(ExtractedClaim(text=text, category="url", position=match.start()))
        return results

    def _extract_general_facts(self, draft: str, seen: set[str]) -> list[ExtractedClaim]:
        """Extracts declarative factual assertion sentences."""
        results: list[ExtractedClaim] = []
        for match in _GENERAL_CLAIM_PATTERN.finditer(draft):
            text = match.group().strip()
            if len(text) >= 20 and text not in seen:
                seen.add(text)
                results.append(ExtractedClaim(text=text, category="general_fact", position=match.start()))
        return results
