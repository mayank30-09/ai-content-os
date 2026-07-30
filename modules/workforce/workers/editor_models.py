"""Editor Worker data models for AI Workforce Core subsystem.

Defines strongly-typed schemas for edit quality scoring and the final
EditedDraftPackage output produced by the EditorWorker pipeline.
"""

from pydantic import BaseModel, Field

from modules.workforce.workers.draft_models import WritingStyle
from modules.workforce.workers.verification_models import VerificationReport


class EditQualityScores(BaseModel):
    """Sub-scores from the EditValidator audit.

    Attributes:
        readability_score: Post-edit readability quality.
        grammar_score: Post-edit grammar quality estimate.
        style_score: Post-edit style and tone consistency.
        citation_preservation_score: Ratio of citations preserved.
        keyword_preservation_score: Ratio of SEO keywords preserved.
        overall_quality: Weighted composite quality score.
    """

    readability_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Readability quality score")
    grammar_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Grammar quality estimate")
    style_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Style and tone consistency")
    citation_preservation_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Citation preservation ratio")
    keyword_preservation_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Keyword preservation ratio")
    overall_quality: float = Field(default=1.0, ge=0.0, le=1.0, description="Weighted composite quality")


class EditedDraftPackage(BaseModel):
    """Strongly-typed production output from the EditorWorker pipeline.

    Attributes:
        original_draft_version: DraftPackage.draft_version from Writer Worker.
        edited_draft_version: Editor revision number.
        title: Finalized draft title.
        subtitle: Optional subtitle or header tagline.
        platform: Target publishing platform.
        content_format: Target format structure.
        audience: Target audience classification.
        objective: Primary content goal.
        writing_style: Writing tone and style enum.
        edited_content: Full markdown body after editing.
        preserved_citations: Citations retained from original draft.
        preserved_keywords: SEO keywords retained from original draft.
        verification_report: Forwarded immutable VerificationReport from Fact Checker.
        quality_scores: EditQualityScores from EditValidator audit.
        editor_metadata: Execution telemetry and version metadata.
    """

    original_draft_version: int = Field(ge=1, description="DraftPackage.draft_version from Writer Worker")
    edited_draft_version: int = Field(default=1, ge=1, description="Editor revision number")
    title: str = Field(description="Finalized draft title")
    subtitle: str | None = Field(default=None, description="Optional subtitle or header tagline")
    platform: str = Field(description="Target publishing platform")
    content_format: str = Field(description="Target format structure")
    audience: str = Field(description="Target audience classification")
    objective: str = Field(description="Primary content goal")
    writing_style: WritingStyle = Field(default=WritingStyle.AUTHORITATIVE, description="Writing tone and style")
    edited_content: str = Field(description="Full markdown body after editing")
    preserved_citations: list[dict] = Field(default_factory=list, description="Citations retained from draft")
    preserved_keywords: list[str] = Field(default_factory=list, description="SEO keywords retained from draft")
    verification_report: VerificationReport = Field(description="Immutable VerificationReport from Fact Checker")
    quality_scores: EditQualityScores = Field(default_factory=EditQualityScores, description="Edit quality sub-scores")
    editor_metadata: dict = Field(
        default_factory=lambda: {
            "editor_version": "v0.6.6",
            "prompt_version": "v1.0.0",
            "edit_pass_count": 1,
        },
        description="Execution telemetry and version metadata",
    )
