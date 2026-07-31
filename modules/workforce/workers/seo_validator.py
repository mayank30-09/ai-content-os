"""SEO Validator for SEO Worker subsystem.

Performs deterministic post-optimization validation to verify that citations
and keywords are preserved, headings are well-structured, meta tags meet
length constraints, and keyword density remains in the optimal range.
"""

import re

from loguru import logger

from modules.workforce.workers.editor_models import EditedDraftPackage
from modules.workforce.workers.seo_analyzer import SEOAnalyzer
from modules.workforce.workers.seo_models import SEOAnalysisResult, SEOScores


class SEOValidator:
    """Deterministic post-optimization SEO quality validator.

    Validates that the optimized content preserves citations and keywords,
    scores heading quality, meta quality, keyword density, and content
    structure. No LLM calls are made.

    This validator is stateless — each ``validate_optimization`` call
    produces a fresh result from the provided inputs.
    """

    META_TITLE_MAX: int = 60
    META_DESC_MAX: int = 160
    OPTIMAL_DENSITY_MIN: float = 1.0
    OPTIMAL_DENSITY_MAX: float = 3.0

    def validate_optimization(
        self,
        original_content: str,
        optimized_content: str,
        edited_pkg: EditedDraftPackage,
        analysis: SEOAnalysisResult,
        meta_title: str = "",
        meta_description: str = "",
    ) -> tuple[SEOScores, list[str]]:
        """Validates the optimized content against the original and source package.

        Args:
            original_content: Original edited content from EditedDraftPackage.
            optimized_content: Content after SEO optimization.
            edited_pkg: EditedDraftPackage containing citations and keywords.
            analysis: SEOAnalysisResult from pre-optimization analysis.
            meta_title: Generated meta title.
            meta_description: Generated meta description.

        Returns:
            Tuple of:
            - SEOScores with all sub-scores computed.
            - List of issue description strings.
        """
        issues: list[str] = []

        citation_score = self._check_citation_preservation(
            edited_pkg.preserved_citations, optimized_content, issues
        )
        keyword_score = self._check_keyword_preservation(
            edited_pkg.preserved_keywords, optimized_content, issues
        )
        heading_score = self._score_heading_quality(optimized_content)
        meta_score = self._score_meta_quality(meta_title, meta_description, issues)

        focus_keyword = edited_pkg.preserved_keywords[0] if edited_pkg.preserved_keywords else ""
        density_score = self._score_keyword_density(optimized_content, focus_keyword)
        structure_score = self._score_content_structure(optimized_content)

        overall = self._calculate_overall_score(
            keyword_density_score=density_score,
            heading_quality_score=heading_score,
            meta_quality_score=meta_score,
            citation_preservation_score=citation_score,
            keyword_preservation_score=keyword_score,
            content_structure_score=structure_score,
        )

        scores = SEOScores(
            keyword_density_score=density_score,
            heading_quality_score=heading_score,
            meta_quality_score=meta_score,
            citation_preservation_score=citation_score,
            keyword_preservation_score=keyword_score,
            content_structure_score=structure_score,
            overall_seo_score=overall,
        )

        logger.info(
            f"SEOValidator: density={density_score:.2f}, heading={heading_score:.2f}, "
            f"meta={meta_score:.2f}, citation_pres={citation_score:.2f}, "
            f"keyword_pres={keyword_score:.2f}, structure={structure_score:.2f}, "
            f"overall={overall:.2f}, issues={len(issues)}"
        )
        return scores, issues

    def _check_citation_preservation(
        self,
        citations: list[dict],
        optimized_content: str,
        issues: list[str],
    ) -> float:
        """Checks that all citation URLs appear in the optimized content.

        Args:
            citations: Citation dicts from EditedDraftPackage.preserved_citations.
            optimized_content: Optimized markdown content.
            issues: Mutable issues list to append findings.

        Returns:
            Citation preservation ratio (0.0–1.0).
        """
        if not citations:
            return 1.0

        total = len(citations)
        preserved = 0
        content_lower = optimized_content.lower()

        for c in citations:
            url = c.get("url", "")
            if url and url.lower() in content_lower:
                preserved += 1
            elif url:
                issues.append(f"Citation URL missing from optimized content: {url}")

        return round(preserved / total, 3) if total > 0 else 1.0

    def _check_keyword_preservation(
        self,
        keywords: list[str],
        optimized_content: str,
        issues: list[str],
    ) -> float:
        """Checks that SEO keywords appear in the optimized content.

        Args:
            keywords: SEO keywords from EditedDraftPackage.preserved_keywords.
            optimized_content: Optimized markdown content.
            issues: Mutable issues list to append findings.

        Returns:
            Keyword preservation ratio (0.0–1.0).
        """
        if not keywords:
            return 1.0

        total = len(keywords)
        preserved = 0
        content_lower = optimized_content.lower()

        for kw in keywords:
            if kw.lower() in content_lower:
                preserved += 1
            else:
                issues.append(f"SEO keyword missing from optimized content: {kw}")

        return round(preserved / total, 3) if total > 0 else 1.0

    def _score_heading_quality(self, content: str) -> float:
        """Scores heading quality based on hierarchy and count.

        Args:
            content: Optimized markdown content.

        Returns:
            Heading quality score (0.0–1.0).
        """
        if not content or not content.strip():
            return 0.5

        headings = SEOAnalyzer.extract_headings(content)
        if not headings:
            return 0.3

        score = 0.5  # Base score for having headings

        # H1 check
        h1_count = sum(1 for h in headings if h["level"] == 1)
        if h1_count == 1:
            score += 0.2

        # Hierarchy check
        hierarchy_valid = True
        prev_level = headings[0]["level"]
        for h in headings[1:]:
            if h["level"] > prev_level + 1:
                hierarchy_valid = False
                break
            prev_level = h["level"]

        if hierarchy_valid:
            score += 0.15

        # Heading count bonus
        if len(headings) >= 3:
            score += 0.15

        return round(min(1.0, score), 3)

    def _score_meta_quality(
        self,
        meta_title: str,
        meta_description: str,
        issues: list[str],
    ) -> float:
        """Scores meta title and description quality.

        Args:
            meta_title: Generated meta title.
            meta_description: Generated meta description.
            issues: Mutable issues list to append findings.

        Returns:
            Meta quality score (0.0–1.0).
        """
        score = 0.0

        # Meta title scoring
        if meta_title:
            score += 0.25
            if len(meta_title) <= self.META_TITLE_MAX:
                score += 0.25
            else:
                issues.append(
                    f"Meta title too long ({len(meta_title)} chars, max {self.META_TITLE_MAX})."
                )

        # Meta description scoring
        if meta_description:
            score += 0.25
            if len(meta_description) <= self.META_DESC_MAX:
                score += 0.25
            else:
                issues.append(
                    f"Meta description too long ({len(meta_description)} chars, max {self.META_DESC_MAX})."
                )

        return round(min(1.0, score), 3)

    def _score_keyword_density(self, content: str, focus_keyword: str) -> float:
        """Scores keyword density based on optimal range adherence.

        Args:
            content: Optimized content.
            focus_keyword: Primary target keyword.

        Returns:
            Keyword density score (0.0–1.0).
        """
        if not content.strip() or not focus_keyword.strip():
            return 0.5

        density = SEOAnalyzer.calculate_keyword_density(content, focus_keyword)

        if self.OPTIMAL_DENSITY_MIN <= density <= self.OPTIMAL_DENSITY_MAX:
            return 1.0
        elif density < self.OPTIMAL_DENSITY_MIN:
            return round(max(0.3, density / self.OPTIMAL_DENSITY_MIN), 3)
        else:
            # Over-optimized
            overshoot = density - self.OPTIMAL_DENSITY_MAX
            return round(max(0.2, 1.0 - (overshoot * 0.15)), 3)

    def _score_content_structure(self, content: str) -> float:
        """Scores content structure quality (paragraphs, length, formatting).

        Args:
            content: Optimized markdown content.

        Returns:
            Content structure score (0.0–1.0).
        """
        if not content or not content.strip():
            return 0.3

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        has_headings = bool(re.search(r"^#{1,6}\s", content, re.MULTILINE))
        word_count = len(content.split())

        score = 0.4  # Base score

        if has_headings:
            score += 0.2
        if len(paragraphs) >= 3:
            score += 0.15
        if word_count >= 500:
            score += 0.15
        if word_count >= 1000:
            score += 0.10

        return round(min(1.0, score), 3)

    @staticmethod
    def _calculate_overall_score(
        keyword_density_score: float,
        heading_quality_score: float,
        meta_quality_score: float,
        citation_preservation_score: float,
        keyword_preservation_score: float,
        content_structure_score: float,
    ) -> float:
        """Calculates weighted composite SEO score.

        Weights:
            - Citation preservation: 0.20 (critical safety)
            - Keyword preservation: 0.15 (critical safety)
            - Keyword density: 0.20
            - Heading quality: 0.15
            - Meta quality: 0.15
            - Content structure: 0.15

        Args:
            keyword_density_score: Density score.
            heading_quality_score: Heading quality score.
            meta_quality_score: Meta quality score.
            citation_preservation_score: Citation preservation ratio.
            keyword_preservation_score: Keyword preservation ratio.
            content_structure_score: Content structure score.

        Returns:
            Weighted overall SEO score (0.0–1.0).
        """
        overall = round(
            (citation_preservation_score * 0.20)
            + (keyword_preservation_score * 0.15)
            + (keyword_density_score * 0.20)
            + (heading_quality_score * 0.15)
            + (meta_quality_score * 0.15)
            + (content_structure_score * 0.15),
            3,
        )
        return min(1.0, overall)
