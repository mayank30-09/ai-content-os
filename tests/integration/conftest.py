"""Shared pytest fixtures for End-to-End Pipeline Integration test suite."""

from pathlib import Path

import pytest

from modules.workflow.models import WorkflowRequest
from modules.workforce.workers.draft_models import WritingStyle
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.publisher_models import PublicationPackage, PublishStatus
from modules.workforce.workers.seo_models import SEOScores
from modules.workforce.workers.verification_models import (
    VerificationReport,
    VerificationStatus,
)


@pytest.fixture
def integration_tmp_dir(tmp_path: Path) -> Path:
    """Fixture providing an isolated temporary directory for integration checkpoints."""
    chk_dir = tmp_path / "integration_checkpoints"
    chk_dir.mkdir(parents=True, exist_ok=True)
    return chk_dir


@pytest.fixture
def sample_e2e_request() -> WorkflowRequest:
    """Fixture providing a standard WorkflowRequest for integration testing."""
    return WorkflowRequest(
        topic="Autonomous AI Integration Architecture",
        keywords=["AI", "Python", "Architecture"],
        target_platform="linkedin",
        content_format="Article",
        audience="Software Engineers",
        objective="EDUCATIONAL",
        writing_style=WritingStyle.AUTHORITATIVE,
        template_name="standard_content_pipeline",
    )


@pytest.fixture
def sample_verification_report() -> VerificationReport:
    """Fixture providing a sample VerificationReport."""
    return VerificationReport(
        overall_status=VerificationStatus.VERIFIED,
        claims_checked=5,
        claims_verified=5,
        overall_confidence=0.96,
    )


@pytest.fixture
def sample_edit_scores() -> EditQualityScores:
    """Fixture providing a sample EditQualityScores."""
    return EditQualityScores(readability_score=0.92, overall_quality=0.94)


@pytest.fixture
def sample_seo_scores() -> SEOScores:
    """Fixture providing a sample SEOScores."""
    return SEOScores(overall_seo_score=0.95)


@pytest.fixture
def sample_publication_package(
    sample_e2e_request: WorkflowRequest,
    sample_verification_report: VerificationReport,
    sample_edit_scores: EditQualityScores,
    sample_seo_scores: SEOScores,
) -> PublicationPackage:
    """Fixture providing a complete PublicationPackage with immutable lineage."""
    return PublicationPackage(
        platform="linkedin",
        title=sample_e2e_request.topic,
        content="Finalized E2E Published Body",
        slug="autonomous-ai-integration-architecture",
        final_url="https://linkedin.com/post/e2e-123456",
        publish_status=PublishStatus.PUBLISHED,
        verification_report=sample_verification_report,
        quality_scores=sample_edit_scores,
        seo_scores=sample_seo_scores,
    )
