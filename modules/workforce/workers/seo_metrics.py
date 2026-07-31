"""SEO Worker telemetry metrics model.

Tracks performance indicators for the SEOWorker pipeline execution.
"""

from pydantic import BaseModel, Field


class SEOWorkerMetrics(BaseModel):
    """Telemetry metrics for the SEOWorker execution pipeline.

    Attributes:
        optimization_time: Total pipeline duration in seconds.
        seo_score_before: Pre-optimization content score from SEOAnalyzer.
        seo_score_after: Post-optimization SEO score from SEOValidator.
        keyword_density: Final focus keyword density percentage.
        heading_score: Heading quality score.
        meta_score: Meta title/description quality score.
        internal_links_suggested: Count of internal link suggestions generated.
        external_links_suggested: Count of external link suggestions generated.
        faq_generated: Whether FAQ section was produced.
        schema_generated: Whether schema markup skeleton was produced.
    """

    optimization_time: float = Field(default=0.0, ge=0.0, description="Pipeline duration in seconds")
    seo_score_before: float = Field(default=0.0, ge=0.0, le=1.0, description="Pre-optimization content score")
    seo_score_after: float = Field(default=0.0, ge=0.0, le=1.0, description="Post-optimization SEO score")
    keyword_density: float = Field(default=0.0, ge=0.0, description="Final focus keyword density %")
    heading_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Heading quality score")
    meta_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Meta quality score")
    internal_links_suggested: int = Field(default=0, ge=0, description="Internal link suggestions count")
    external_links_suggested: int = Field(default=0, ge=0, description="External link suggestions count")
    faq_generated: bool = Field(default=False, description="FAQ section produced")
    schema_generated: bool = Field(default=False, description="Schema markup skeleton produced")
