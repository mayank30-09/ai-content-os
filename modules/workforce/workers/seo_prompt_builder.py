"""SEO optimization prompt builder for SEO Worker subsystem.

Assembles structured optimization prompts for the GeminiWebProvider,
embedding the edited draft, analysis results, keyword targets, and
explicit constraints to preserve factual accuracy while improving SEO.
"""

from modules.workforce.workers.editor_models import EditedDraftPackage
from modules.workforce.workers.seo_models import SEOAnalysisResult


class SEOPromptBuilder:
    """Builds structured SEO optimization prompts for AI-assisted content improvement.

    Produces prompts that instruct the language model to optimize headings,
    keyword placement, generate meta title/description, FAQ section, schema
    markup skeleton, and link suggestions — while explicitly forbidding
    changes to facts, statistics, dates, and citations.

    This builder is stateless. Each call produces a fresh prompt string.
    """

    PROMPT_VERSION: str = "v1.0.0"

    def build_system_instruction(self) -> str:
        """Returns the system-level persona instruction for the SEO optimization session.

        Returns:
            System instruction string for a professional SEO specialist persona.
        """
        return (
            "You are a professional SEO specialist with expertise in on-page optimization. "
            "Your role is to optimize the provided content for search engines while preserving "
            "all facts, statistics, numbers, dates, citations, and editorial quality. "
            "You MUST NOT invent facts or change factual meaning. "
            "You MUST NOT remove or alter any citations or URLs. "
            "You MUST return a valid JSON response with the exact structure requested. "
            "Focus on: heading optimization, keyword placement, meta tags, FAQ generation, "
            "schema markup skeleton, and link suggestions."
        )

    def build_optimization_prompt(
        self,
        edited_pkg: EditedDraftPackage,
        analysis: SEOAnalysisResult,
    ) -> str:
        """Builds a structured SEO optimization prompt from an EditedDraftPackage and analysis.

        Args:
            edited_pkg: EditedDraftPackage from the Editor Worker.
            analysis: SEOAnalysisResult from the SEOAnalyzer.

        Returns:
            Formatted optimization prompt string.
        """
        keyword_block = self._build_keyword_block(
            edited_pkg.preserved_keywords[0] if edited_pkg.preserved_keywords else "",
            edited_pkg.preserved_keywords,
        )
        heading_block = self._build_heading_guidance(analysis.heading_analysis)
        meta_block = self._build_meta_block(analysis.meta_analysis)
        constraints_block = self._build_constraints_block()

        return f"""## SEO OPTIMIZATION TASK

Optimize the following content for search engines. Return a JSON response.

{constraints_block}
{keyword_block}
{heading_block}
{meta_block}
### ANALYSIS FINDINGS

- Current keyword density: {analysis.current_keyword_density:.2f}%
- Content length: {analysis.content_length} words
- Content score: {analysis.content_score:.2f}
- Issues found: {len(analysis.issues)}
{self._format_issues(analysis.issues)}

### SCHEMA OPPORTUNITIES

Applicable schema types: {', '.join(analysis.schema_opportunities)}

### FAQ OPPORTUNITIES

{self._format_faq_opportunities(analysis.faq_opportunities)}

### ORIGINAL CONTENT

{edited_pkg.edited_content}

### CITATIONS — PRESERVE ALL

{self._format_citations(edited_pkg.preserved_citations)}

### REQUIRED JSON OUTPUT FORMAT

Return ONLY a valid JSON object with this exact structure:
```json
{{
  "optimized_content": "Full optimized markdown content",
  "meta_title": "SEO meta title (max 60 chars)",
  "meta_description": "SEO meta description (max 160 chars)",
  "faq_section": [
    {{"question": "...", "answer": "..."}}
  ],
  "schema_markup": {{
    "@type": "Article",
    "headline": "...",
    "author": "{{{{AUTHOR}}}}",
    "datePublished": "{{{{DATE}}}}",
    "url": "{{{{CANONICAL_URL}}}}"
  }},
  "internal_link_suggestions": [
    {{"anchor_text": "...", "target_topic": "...", "rationale": "..."}}
  ],
  "external_link_suggestions": [
    {{"anchor_text": "...", "target_topic": "...", "rationale": "..."}}
  ],
  "image_alt_suggestions": [
    {{"image_ref": "...", "alt_text": "..."}}
  ]
}}
```"""

    def _build_constraints_block(self) -> str:
        """Builds the SEO optimization constraints block.

        Returns:
            Formatted constraints block string.
        """
        return """### CONSTRAINTS — DO NOT VIOLATE

1. DO NOT change any facts, statistics, numbers, or dates.
2. DO NOT remove or alter any citations or URLs.
3. DO NOT add new facts or claims not present in the original.
4. DO NOT change the overall meaning of any section.
5. Preserve all existing citations and URLs exactly.
6. Optimize headings to include keywords naturally.
7. Ensure keyword density stays in the 1%–3% range.
8. Generate meta title ≤60 characters, meta description ≤160 characters.
9. Schema markup MUST use {{PLACEHOLDER}} syntax for runtime values.
10. Link suggestions MUST use target_topic (not final URLs).
"""

    def _build_keyword_block(self, focus_keyword: str, all_keywords: list[str]) -> str:
        """Builds the keyword targeting block.

        Args:
            focus_keyword: Primary target keyword.
            all_keywords: All target keywords including secondary.

        Returns:
            Formatted keyword block string.
        """
        if not all_keywords:
            return "### TARGET KEYWORDS\n\nNo keywords specified.\n"

        secondary = [kw for kw in all_keywords if kw != focus_keyword]
        lines = ["### TARGET KEYWORDS\n"]
        lines.append(f"- **Focus keyword**: {focus_keyword}")
        if secondary:
            lines.append(f"- **Secondary keywords**: {', '.join(secondary)}")
        lines.append("")
        return "\n".join(lines)

    def _build_heading_guidance(self, heading_analysis) -> str:
        """Builds heading optimization guidance from analysis.

        Args:
            heading_analysis: HeadingAnalysis from SEOAnalyzer.

        Returns:
            Formatted heading guidance block string.
        """
        lines = ["### HEADING OPTIMIZATION GUIDANCE\n"]

        if not heading_analysis.has_h1:
            lines.append("- **Critical**: Add exactly one H1 heading.")
        if not heading_analysis.heading_hierarchy_valid:
            lines.append("- **Warning**: Fix heading hierarchy — do not skip levels.")
        if heading_analysis.heading_count < 3:
            lines.append("- Add more subheadings to improve content structure.")

        if heading_analysis.headings:
            lines.append("\nCurrent headings:")
            for h in heading_analysis.headings:
                lines.append(f"  - H{h['level']}: {h['text']}")

        lines.append("")
        return "\n".join(lines)

    def _build_meta_block(self, meta_analysis) -> str:
        """Builds meta optimization guidance from analysis.

        Args:
            meta_analysis: MetaAnalysis from SEOAnalyzer.

        Returns:
            Formatted meta guidance block string.
        """
        lines = ["### META OPTIMIZATION GUIDANCE\n"]
        lines.append(f"- Current title length: {meta_analysis.title_length} chars (max {60})")
        lines.append(f"- Title has focus keyword: {meta_analysis.title_has_keyword}")

        if meta_analysis.suggested_slug:
            lines.append(f"- Suggested slug: {meta_analysis.suggested_slug}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_issues(issues: list[str]) -> str:
        """Formats analysis issues as a bulleted list.

        Args:
            issues: List of issue description strings.

        Returns:
            Formatted issues string.
        """
        if not issues:
            return ""
        return "\n".join(f"  - {issue}" for issue in issues)

    @staticmethod
    def _format_faq_opportunities(faqs: list[str]) -> str:
        """Formats FAQ opportunities as a bulleted list.

        Args:
            faqs: List of FAQ-worthy question strings.

        Returns:
            Formatted FAQ opportunities string.
        """
        if not faqs:
            return "No FAQ opportunities detected. Generate 2–3 relevant FAQs from the content."
        return "\n".join(f"- {faq}" for faq in faqs)

    @staticmethod
    def _format_citations(citations: list[dict]) -> str:
        """Formats citations for preservation reference.

        Args:
            citations: List of citation dicts.

        Returns:
            Formatted citations string.
        """
        if not citations:
            return "No citations to preserve."
        lines = []
        for c in citations:
            url = c.get("url", "")
            title = c.get("title", "Untitled")
            lines.append(f"- [{title}]({url})")
        return "\n".join(lines)
