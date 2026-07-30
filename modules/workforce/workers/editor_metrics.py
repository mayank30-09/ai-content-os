"""Editor Worker telemetry metrics model.

Tracks performance indicators for the EditorWorker pipeline execution.
"""

from pydantic import BaseModel, Field


class EditorWorkerMetrics(BaseModel):
    """Telemetry metrics for the EditorWorker execution pipeline.

    Attributes:
        editing_time: Total pipeline duration in seconds.
        readability_before: Pre-edit readability estimate.
        readability_after: Post-edit readability estimate.
        grammar_improvement: Grammar score delta (after - before).
        style_improvement: Style score delta.
        citation_preservation: Ratio of citations preserved.
        keyword_preservation: Ratio of SEO keywords preserved.
        overall_quality: Composite quality score.
    """

    editing_time: float = Field(default=0.0, ge=0.0, description="Pipeline duration in seconds")
    readability_before: float = Field(default=1.0, ge=0.0, le=1.0, description="Pre-edit readability estimate")
    readability_after: float = Field(default=1.0, ge=0.0, le=1.0, description="Post-edit readability estimate")
    grammar_improvement: float = Field(default=0.0, ge=-1.0, le=1.0, description="Grammar score delta")
    style_improvement: float = Field(default=0.0, ge=-1.0, le=1.0, description="Style score delta")
    citation_preservation: float = Field(default=1.0, ge=0.0, le=1.0, description="Citation preservation ratio")
    keyword_preservation: float = Field(default=1.0, ge=0.0, le=1.0, description="Keyword preservation ratio")
    overall_quality: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite quality score")
