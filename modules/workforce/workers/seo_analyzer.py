"""SEO Analyzer for SEO Worker subsystem.

Performs deterministic pre-optimization analysis of content to measure
current SEO fitness and identify improvement opportunities. No LLM calls.
"""

import re

from loguru import logger

from modules.workforce.workers.seo_models import (
    HeadingAnalysis,
    MetaAnalysis,
    SEOAnalysisResult,
)


class SEOAnalyzer:
    """Deterministic SEO content analyzer.

    Evaluates content for keyword density, heading hierarchy, meta fitness,
    FAQ opportunities, schema opportunities, and content structure. Produces
    an ``SEOAnalysisResult`` with diagnostics and a baseline content score.

    This analyzer is stateless — each ``analyze`` call produces a fresh result.
    """

    # Optimal keyword density range (percentage)
    OPTIMAL_DENSITY_MIN: float = 1.0
    OPTIMAL_DENSITY_MAX: float = 3.0

    # Meta length constraints
    META_TITLE_MAX: int = 60
    META_DESC_MAX: int = 160

    def analyze(
        self,
        content: str,
        title: str,
        focus_keyword: str,
        secondary_keywords: list[str],
        citations: list[dict],
    ) -> SEOAnalysisResult:
        """Analyzes content for SEO fitness and improvement opportunities.

        Args:
            content: Full markdown content body.
            title: Content title.
            focus_keyword: Primary target keyword.
            secondary_keywords: Supporting target keywords.
            citations: Citation dicts from upstream draft.

        Returns:
            SEOAnalysisResult with diagnostics and baseline score.
        """
        issues: list[str] = []

        keyword_density = self._calculate_keyword_density(content, focus_keyword)
        heading_analysis = self._analyze_heading_structure(content)
        meta_analysis = self._analyze_meta_fitness(title, focus_keyword)
        content_length = len(content.split())
        faq_opportunities = self._detect_faq_opportunities(content)
        schema_opportunities = self._detect_schema_opportunities(content, title)

        # Collect issues from sub-analyses
        issues.extend(heading_analysis.issues)
        issues.extend(meta_analysis.issues)

        # Keyword density diagnostics
        if keyword_density < self.OPTIMAL_DENSITY_MIN:
            issues.append(
                f"Keyword density ({keyword_density:.2f}%) below optimal range "
                f"({self.OPTIMAL_DENSITY_MIN}%–{self.OPTIMAL_DENSITY_MAX}%)."
            )
        elif keyword_density > self.OPTIMAL_DENSITY_MAX:
            issues.append(
                f"Keyword density ({keyword_density:.2f}%) above optimal range "
                f"({self.OPTIMAL_DENSITY_MIN}%–{self.OPTIMAL_DENSITY_MAX}%). Risk of keyword stuffing."
            )

        # Content length diagnostics
        if content_length < 300:
            issues.append(f"Content length ({content_length} words) is below recommended 300 words.")

        content_score = self._calculate_content_score(
            keyword_density, heading_analysis, meta_analysis, content_length
        )

        logger.info(
            f"SEOAnalyzer: keyword_density={keyword_density:.2f}%, "
            f"headings={heading_analysis.heading_count}, "
            f"content_length={content_length}, "
            f"content_score={content_score:.2f}, issues={len(issues)}"
        )

        return SEOAnalysisResult(
            current_keyword_density=keyword_density,
            heading_analysis=heading_analysis,
            meta_analysis=meta_analysis,
            content_length=content_length,
            faq_opportunities=faq_opportunities,
            schema_opportunities=schema_opportunities,
            content_score=content_score,
            issues=issues,
        )

    def _calculate_keyword_density(self, content: str, focus_keyword: str) -> float:
        """Calculates focus keyword density as a percentage of total words."""
        return self.calculate_keyword_density(content, focus_keyword)

    @staticmethod
    def calculate_keyword_density(content: str, focus_keyword: str) -> float:
        """Calculates focus keyword density as a percentage of total words.

        Args:
            content: Content text.
            focus_keyword: Primary target keyword.

        Returns:
            Keyword density percentage (0.0+).
        """
        if not content.strip() or not focus_keyword.strip():
            return 0.0

        words = content.lower().split()
        total_words = len(words)
        if total_words == 0:
            return 0.0

        keyword_lower = focus_keyword.lower()
        keyword_words = keyword_lower.split()
        keyword_len = len(keyword_words)

        if keyword_len == 0:
            return 0.0

        # Count occurrences of the keyword phrase
        occurrences = 0
        content_lower = content.lower()
        start = 0
        while True:
            pos = content_lower.find(keyword_lower, start)
            if pos == -1:
                break
            occurrences += 1
            start = pos + 1

        density = (occurrences * keyword_len / total_words) * 100
        return round(density, 2)

    @staticmethod
    def extract_headings(content: str) -> list[dict]:
        """Extracts heading structure from markdown content.

        Args:
            content: Markdown content.

        Returns:
            List of heading dicts with ``level`` and ``text`` keys.
        """
        headings: list[dict] = []
        if not content:
            return headings
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        matches = heading_pattern.findall(content)
        for hashes, text in matches:
            headings.append({"level": len(hashes), "text": text.strip()})
        return headings

    def _analyze_heading_structure(self, content: str) -> HeadingAnalysis:
        """Analyzes heading hierarchy for SEO compliance.

        Args:
            content: Full markdown content.

        Returns:
            HeadingAnalysis with hierarchy validation and diagnostics.
        """
        issues: list[str] = []
        headings = self.extract_headings(content)

        h1_count = sum(1 for h in headings if h["level"] == 1)
        has_h1 = h1_count == 1

        if h1_count == 0:
            issues.append("No H1 heading found. Each page should have exactly one H1.")
        elif h1_count > 1:
            issues.append(f"Multiple H1 headings found ({h1_count}). Use exactly one H1.")

        # Check hierarchy — no skipped levels
        hierarchy_valid = True
        if headings:
            prev_level = headings[0]["level"]
            for h in headings[1:]:
                if h["level"] > prev_level + 1:
                    hierarchy_valid = False
                    issues.append(
                        f"Heading hierarchy skip: H{prev_level} → H{h['level']}. "
                        f"Do not skip heading levels."
                    )
                prev_level = h["level"]

        return HeadingAnalysis(
            has_h1=has_h1,
            heading_count=len(headings),
            heading_hierarchy_valid=hierarchy_valid,
            headings=headings,
            issues=issues,
        )

    def _analyze_meta_fitness(self, title: str, focus_keyword: str) -> MetaAnalysis:
        """Analyzes title and generates meta suggestions.

        Args:
            title: Content title.
            focus_keyword: Primary target keyword.

        Returns:
            MetaAnalysis with suggestions and diagnostics.
        """
        issues: list[str] = []
        title_length = len(title)
        title_has_keyword = focus_keyword.lower() in title.lower() if focus_keyword else False

        if title_length > self.META_TITLE_MAX:
            issues.append(
                f"Title length ({title_length} chars) exceeds meta title limit of {self.META_TITLE_MAX}."
            )

        if not title_has_keyword and focus_keyword:
            issues.append(f"Focus keyword '{focus_keyword}' not found in title.")

        # Generate meta suggestions
        suggested_meta_title = title[:self.META_TITLE_MAX] if title else ""
        suggested_meta_description = self._generate_meta_description(title, focus_keyword)
        suggested_slug = self._generate_slug(title)

        return MetaAnalysis(
            title_length=title_length,
            title_has_keyword=title_has_keyword,
            suggested_meta_title=suggested_meta_title,
            suggested_meta_description=suggested_meta_description,
            suggested_slug=suggested_slug,
            issues=issues,
        )

    def _detect_faq_opportunities(self, content: str) -> list[str]:
        """Detects question-like sentences that could form an FAQ section.

        Args:
            content: Content text.

        Returns:
            List of detected question strings.
        """
        questions: list[str] = []
        # Match lines ending with ? or starting with interrogative words
        question_pattern = re.compile(
            r"(?:^|\n)\s*(?:(?:What|How|Why|When|Where|Who|Which|Can|Do|Does|Is|Are|Should|Will|Would)\s+.+\??)",
            re.IGNORECASE,
        )
        matches = question_pattern.findall(content)
        for match in matches:
            cleaned = match.strip()
            if cleaned and len(cleaned.split()) >= 4:
                questions.append(cleaned)
        return questions[:5]  # Cap at 5 FAQ opportunities

    def _detect_schema_opportunities(self, content: str, title: str) -> list[str]:
        """Detects applicable JSON-LD schema types for the content.

        Args:
            content: Content text.
            title: Content title.

        Returns:
            List of applicable schema type strings.
        """
        schemas: list[str] = ["Article"]  # Always applicable

        # FAQ schema if questions are detected
        if re.search(r"\?", content):
            schemas.append("FAQPage")

        # HowTo schema if step-like content is detected
        if re.search(r"(?:step\s*\d|^\s*\d+\.\s)", content, re.IGNORECASE | re.MULTILINE):
            schemas.append("HowTo")

        return schemas

    def _calculate_content_score(
        self,
        keyword_density: float,
        heading_analysis: HeadingAnalysis,
        meta_analysis: MetaAnalysis,
        content_length: int,
    ) -> float:
        """Calculates a composite pre-optimization content score.

        Args:
            keyword_density: Current keyword density percentage.
            heading_analysis: Heading structure analysis.
            meta_analysis: Meta fitness analysis.
            content_length: Word count.

        Returns:
            Content score (0.0–1.0).
        """
        score = 0.0

        # Keyword density contribution (0.25)
        if self.OPTIMAL_DENSITY_MIN <= keyword_density <= self.OPTIMAL_DENSITY_MAX:
            score += 0.25
        elif keyword_density > 0:
            score += 0.10

        # Heading quality contribution (0.25)
        if heading_analysis.has_h1:
            score += 0.10
        if heading_analysis.heading_hierarchy_valid:
            score += 0.10
        if heading_analysis.heading_count >= 3:
            score += 0.05

        # Meta fitness contribution (0.25)
        if meta_analysis.title_has_keyword:
            score += 0.15
        if meta_analysis.title_length <= self.META_TITLE_MAX:
            score += 0.10

        # Content length contribution (0.25)
        if content_length >= 1000:
            score += 0.25
        elif content_length >= 500:
            score += 0.15
        elif content_length >= 300:
            score += 0.10

        return round(min(1.0, score), 3)

    @staticmethod
    def _generate_meta_description(title: str, focus_keyword: str) -> str:
        """Generates a baseline meta description from the title and keyword.

        Args:
            title: Content title.
            focus_keyword: Primary target keyword.

        Returns:
            Meta description string (<=160 chars).
        """
        if not title:
            return ""
        desc = f"Learn about {title.lower()}"
        if focus_keyword and focus_keyword.lower() not in desc.lower():
            desc += f" — covering {focus_keyword}"
        desc += "."
        return desc[:160]

    @staticmethod
    def _generate_slug(title: str) -> str:
        """Generates a URL-safe slug from the title.

        Args:
            title: Content title.

        Returns:
            URL-safe slug string.
        """
        if not title:
            return ""
        slug = title.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug)
        slug = slug.strip("-")
        return slug[:80]
