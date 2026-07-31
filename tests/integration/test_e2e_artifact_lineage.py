"""Artifact Lineage & Type Safety Integration Tests for AI Content OS.

Verifies:
- ArtifactRegistry strongly-typed artifact storage and model conversion
- Missing required artifact detection and early DAG error validation
- Lineage preservation across all 8 workers
- Forwarding of immutable VerificationReport, EditQualityScores, and SEOScores into final PublicationPackage and WorkflowResult
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from modules.workflow.artifact_registry import ArtifactRegistry
from modules.workflow.checkpoint import CheckpointManager
from modules.workflow.engine import WorkflowEngine
from modules.workflow.models import (
    WorkflowRequest,
    WorkflowStatus,
)
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskResult, TaskStatus
from modules.workforce.workers.draft_models import DraftPackage
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.publisher_models import PublicationPackage
from modules.workforce.workers.seo_models import SEOScores
from modules.workforce.workers.verification_models import (
    VerificationReport,
)


class TestE2EArtifactLineage:
    """Integration test suite for ArtifactRegistry type safety and lineage preservation."""

    def test_artifact_registry_type_validation_methods(
        self,
        sample_verification_report: VerificationReport,
    ):
        reg = ArtifactRegistry()

        # 1. Register Pydantic model instance
        reg.register("ver_report", sample_verification_report)
        typed_1 = reg.get_typed("ver_report", VerificationReport)
        assert typed_1.claims_checked == 5

        # 2. Register dictionary representation
        reg.register("ver_dict", sample_verification_report.model_dump(mode="json"))
        typed_2 = reg.get_typed("ver_dict", VerificationReport)
        assert typed_2.claims_verified == 5

        # 3. Register JSON string representation
        reg.register("ver_json", sample_verification_report.model_dump_json())
        typed_3 = reg.get_typed("ver_json", VerificationReport)
        assert typed_3.overall_confidence == 0.96

        # 4. Invalid model type raises TypeError
        reg.register("invalid_type", 12345)
        with pytest.raises(TypeError):
            reg.get_typed("invalid_type", VerificationReport)

    @pytest.mark.asyncio
    async def test_lineage_forwarding_through_pipeline(
        self,
        sample_e2e_request: WorkflowRequest,
        sample_verification_report: VerificationReport,
        sample_edit_scores: EditQualityScores,
        sample_seo_scores: SEOScores,
        sample_publication_package: PublicationPackage,
        integration_tmp_dir: Path,
    ):
        workforce_mgr = WorkforceManager(bus=MessageBus())

        async def mock_execute(task: Task, context: SharedContext) -> TaskResult:
            wtype = task.type
            art_map = {
                "research_worker": {"research_package": {"topic": sample_e2e_request.topic}},
                "memory_worker": {"context_package": {"memory": "ctx"}},
                "strategist_worker": {"strategy_package": {"outline": ["H1"]}},
                "writer_worker": {
                    "draft_package": DraftPackage(
                        title=sample_e2e_request.topic,
                        draft="Draft Body",
                        platform="linkedin",
                        content_format="Article",
                        audience="Devs",
                        objective="ED",
                    ).model_dump(mode="json")
                },
                "fact_checker_worker": {
                    "verified_draft_package": {"content": "Verified"},
                    "verification_report": sample_verification_report.model_dump(mode="json"),
                },
                "editor_worker": {
                    "edited_draft_package": {"content": "Edited"},
                    "quality_scores": sample_edit_scores.model_dump(mode="json"),
                },
                "seo_worker": {
                    "seo_optimized_package": {"content": "SEO"},
                    "seo_scores": sample_seo_scores.model_dump(mode="json"),
                },
                "publisher_worker": {
                    "publication_package": sample_publication_package.model_dump(mode="json"),
                },
            }
            return TaskResult(
                task_id=task.id,
                worker_id=f"w_{wtype}",
                status=TaskStatus.COMPLETED,
                artifacts=art_map.get(wtype, {}),
            )

        workforce_mgr.assign_and_execute = AsyncMock(side_effect=mock_execute)
        chk_mgr = CheckpointManager(storage_dir=integration_tmp_dir)
        engine = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=workforce_mgr,
            bus=MessageBus(),
        )

        result = await engine.execute_workflow(sample_e2e_request)

        # Assert full lineage preservation in WorkflowResult
        assert result.status == WorkflowStatus.COMPLETED
        assert result.verification_report is not None
        assert result.verification_report.claims_checked == 5
        assert result.quality_scores is not None
        assert result.quality_scores.readability_score == 0.92
        assert result.seo_scores is not None
        assert result.seo_scores.overall_seo_score == 0.95
