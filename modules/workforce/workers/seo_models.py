"""SEO Worker data models for AI Workforce Core subsystem.

Defines strongly-typed schemas for SEO analysis results, scoring,
and the final SEOOptimizedPackage output produced by the SEOWorker pipeline.
"""

from pydantic import BaseModel, Field

from modules.workforce.workers.draft_models import WritingStyle
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.verification_models import VerificationReport


class HeadingAnalysis(BaseModel):
    """Analysis of document heading structure and hierarchy.

    Attributes:
        has_h1: Whether the document contains exactly one H1.
        heading_count: Total number of headings found.
        heading_hierarchy_valid: Whether heading levels are sequential (no skips).
        headings: List of heading dicts with ``level`` and ``text`` keys.
        issues: Diagnostic messages for heading problems.
    """

    has_h1: bool = Field(default=False, description="Single H1 present in document")
    heading_count: int = Field(default=0, ge=0, description="Total heading count")
    heading_hierarchy_valid: bool = Field(default=True, description="No skipped heading levels")
    headings: list[dict] = Field(default_factory=list, description="Heading entries [{level, text}]")
    issues: list[str] = Field(default_factory=list, description="Heading diagnostic messages")


class MetaAnalysis(BaseModel):
    """Analysis of title and meta description fitness for SEO.

    Attributes:
        title_length: Character count of the content title.
        title_has_keyword: Whether the focus keyword appears in the title.
        suggested_meta_title: Generated meta title (<=60 chars).
        suggested_meta_description: Generated meta description (<=160 chars).
        suggested_slug: URL-safe slug derived from the title.
        issues: Diagnostic messages for meta problems.
    """

    title_length: int = Field(default=0, ge=0, description="Title character count")
    title_has_keyword: bool = Field(default=False, description="Focus keyword present in title")
    suggested_meta_title: str = Field(default="", description="Generated meta title <=60 chars")
    suggested_meta_description: str = Field(default="", description="Generated meta description <=160 chars")
    suggested_slug: str = Field(default="", description="URL-safe slug from title")
    issues: list[str] = Field(default_factory=list, description="Meta diagnostic messages")


class SEOAnalysisResult(BaseModel):
    """Pre-optimization SEO analysis produced by the SEOAnalyzer.

    Attributes:
        current_keyword_density: Current focus keyword density percentage.
        heading_analysis: Heading structure analysis.
        meta_analysis: Meta title/description fitness analysis.
        content_length: Word count of the content.
        faq_opportunities: Detected FAQ-worthy questions from the content.
        schema_opportunities: Detected schema types applicable to the content.
        content_score: Pre-optimization baseline SEO score.
        issues: All diagnostic findings from analysis.
    """

    current_keyword_density: float = Field(default=0.0, ge=0.0, description="Focus keyword density %")
    heading_analysis: HeadingAnalysis = Field(default_factory=HeadingAnalysis, description="Heading structure analysis")
    meta_analysis: MetaAnalysis = Field(default_factory=MetaAnalysis, description="Meta fitness analysis")
    content_length: int = Field(default=0, ge=0, description="Content word count")
    faq_opportunities: list[str] = Field(default_factory=list, description="Detected FAQ-worthy questions")
    schema_opportunities: list[str] = Field(default_factory=list, description="Applicable schema types")
    content_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Pre-optimization baseline score")
    issues: list[str] = Field(default_factory=list, description="All diagnostic findings")


class SEOScores(BaseModel):
    """Sub-scores from the SEOValidator post-optimization audit.

    Attributes:
        keyword_density_score: Keyword density within optimal range.
        heading_quality_score: Heading hierarchy and keyword presence.
        meta_quality_score: Meta title/description quality.
        citation_preservation_score: Ratio of citations preserved.
        keyword_preservation_score: Ratio of SEO keywords preserved.
        content_structure_score: Content structure quality (paragraphs, length, links).
        overall_seo_score: Weighted composite SEO score.
    """

    keyword_density_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Keyword density score")
    heading_quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Heading quality score")
    meta_quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Meta quality score")
    citation_preservation_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Citation preservation ratio")
    keyword_preservation_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Keyword preservation ratio")
    content_structure_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Content structure score")
    overall_seo_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Weighted composite SEO score")


class SEOOptimizedPackage(BaseModel):
    """Strongly-typed production output from the SEOWorker pipeline.

    Attributes:
        title: Content title (may be refined for SEO).
        meta_title: SEO meta title (<=60 chars).
        meta_description: SEO meta description (<=160 chars).
        slug: URL-safe slug.
        focus_keyword: Primary target keyword.
        secondary_keywords: Supporting target keywords.
        keyword_density: Final focus keyword density percentage.
        optimized_content: Full markdown body after SEO optimization.
        heading_structure: Heading entries [{level, text}].
        faq_section: Generated FAQ entries [{question, answer}].
        internal_link_suggestions: Internal link suggestions [{anchor_text, target_topic, rationale}].
        external_link_suggestions: External link suggestions [{anchor_text, target_topic, rationale}].
        schema_markup: JSON-LD skeleton with placeholders for runtime values.
        image_alt_suggestions: Image alt text suggestions [{image_ref, alt_text}].
        readability_score: Forwarded readability score from editor.
        seo_score: Overall SEO score from SEOValidator.
        seo_scores: SEOScores sub-score breakdown.
        verification_report: Forwarded immutable VerificationReport from Fact Checker.
        quality_scores: Forwarded immutable EditQualityScores from Editor.
        platform: Target publishing platform.
        content_format: Target format structure.
        audience: Target audience classification.
        objective: Primary content goal.
        writing_style: Writing tone and style enum.
        optimization_metadata: Execution telemetry and version metadata.
    """

    # Identity
    title: str = Field(description="Content title")
    meta_title: str = Field(default="", description="SEO meta title <=60 chars")
    meta_description: str = Field(default="", description="SEO meta description <=160 chars")
    slug: str = Field(default="", description="URL-safe slug")

    # Keywords
    focus_keyword: str = Field(default="", description="Primary target keyword")
    secondary_keywords: list[str] = Field(default_factory=list, description="Supporting keywords")
    keyword_density: float = Field(default=0.0, ge=0.0, description="Focus keyword density %")

    # Content
    optimized_content: str = Field(description="Full markdown body after SEO optimization")
    heading_structure: list[dict] = Field(default_factory=list, description="Heading entries [{level, text}]")
    faq_section: list[dict] = Field(default_factory=list, description="FAQ entries [{question, answer}]")

    # Links (hybrid: AI suggests topic, Publisher resolves URL)
    internal_link_suggestions: list[dict] = Field(
        default_factory=list,
        description="Internal link suggestions [{anchor_text, target_topic, rationale}]",
    )
    external_link_suggestions: list[dict] = Field(
        default_factory=list,
        description="External link suggestions [{anchor_text, target_topic, rationale}]",
    )

    # Technical SEO
    schema_markup: dict = Field(
        default_factory=dict,
        description="JSON-LD skeleton with {{PLACEHOLDER}} values for Publisher",
    )
    image_alt_suggestions: list[dict] = Field(
        default_factory=list,
        description="Image alt text suggestions [{image_ref, alt_text}]",
    )

    # Scores
    readability_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Forwarded readability score")
    seo_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall SEO score")
    seo_scores: SEOScores = Field(default_factory=SEOScores, description="SEO sub-scores breakdown")

    # Lineage (immutable forwards)
    verification_report: VerificationReport = Field(description="Immutable VerificationReport from Fact Checker")
    quality_scores: EditQualityScores = Field(
        default_factory=EditQualityScores,
        description="Immutable EditQualityScores from Editor",
    )

    # Context
    platform: str = Field(description="Target publishing platform")
    content_format: str = Field(description="Target format structure")
    audience: str = Field(description="Target audience classification")
    objective: str = Field(description="Primary content goal")
    writing_style: WritingStyle = Field(default=WritingStyle.AUTHORITATIVE, description="Writing tone and style")

    # Metadata
    optimization_metadata: dict = Field(
        default_factory=lambda: {
            "seo_version": "v0.6.7",
            "prompt_version": "v1.0.0",
            "optimization_pass_count": 1,
        },
        description="Execution telemetry and version metadata",
    )
