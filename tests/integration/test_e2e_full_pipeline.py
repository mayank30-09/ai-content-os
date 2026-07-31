"""Full End-to-End Pipeline Integration Test for AI Content OS.

Validates that a single WorkflowRequest executes through all 8 production workers in sequence:
Research Worker → Memory Worker → Content Strategist → Writer Worker → Fact Checker → Editor Worker → SEO Worker → Publisher Worker

Verifies:
- Complete workflow execution status COMPLETED
- 8 steps completed in topological order
- PublicationPackage generation with valid URL
- Immutable lineage forwarding (VerificationReport, EditQualityScores, SEOScores)
- Execution metrics summary
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

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
from modules.workforce.workers.publisher_models import PublicationPackage, PublishStatus
from modules.workforce.workers.seo_models import SEOScores
from modules.workforce.workers.verification_models import VerificationReport


@pytest.fixture
def integrated_workforce_manager(
    sample_e2e_request: WorkflowRequest,
    sample_verification_report: VerificationReport,
    sample_edit_scores: EditQualityScores,
    sample_seo_scores: SEOScores,
    sample_publication_package: PublicationPackage,
) -> WorkforceManager:
    """WorkforceManager fixture configured for end-to-end multi-worker pipeline simulation."""
    mgr = WorkforceManager(bus=MessageBus())

    async def mock_assign_and_execute(task: Task, context: SharedContext) -> TaskResult:
        worker_type = task.type

        artifact_responses = {
            "research_worker": {
                "research_package": {
                    "topic": sample_e2e_request.topic,
                    "facts": ["Fact 1: AI OS is modular.", "Fact 2: Python 3.14 recommended."],
                }
            },
            "memory_worker": {
                "context_package": {
                    "institutional_memory": "Institutional knowledge on AI Content OS architecture."
                }
            },
            "strategist_worker": {
                "strategy_package": {
                    "title": sample_e2e_request.topic,
                    "outline": ["H1: Overview", "H2: Architecture", "H3: Conclusion"],
                }
            },
            "writer_worker": {
                "draft_package": DraftPackage(
                    title=sample_e2e_request.topic,
                    draft="# Autonomous AI Integration Architecture\n\nFull draft body content.",
                    platform="linkedin",
                    content_format="Article",
                    audience="Software Engineers",
                    objective="EDUCATIONAL",
                ).model_dump(mode="json")
            },
            "fact_checker_worker": {
                "verified_draft_package": {
                    "verified_content": "Verified content body",
                    "report": sample_verification_report.model_dump(mode="json"),
                },
                "verification_report": sample_verification_report.model_dump(mode="json"),
            },
            "editor_worker": {
                "edited_draft_package": {"edited_content": "Edited content body"},
                "quality_scores": sample_edit_scores.model_dump(mode="json"),
            },
            "seo_worker": {
                "seo_optimized_package": {"optimized_content": "SEO optimized content body"},
                "seo_scores": sample_seo_scores.model_dump(mode="json"),
            },
            "publisher_worker": {
                "publication_package": sample_publication_package.model_dump(mode="json"),
            },
        }

        artifacts = artifact_responses.get(worker_type, {"output": "default"})
        return TaskResult(
            task_id=task.id,
            worker_id=f"prod_worker_{worker_type}",
            status=TaskStatus.COMPLETED,
            execution_time=0.02,
            artifacts=artifacts,
            logs=[f"Worker {worker_type} completed execution."],
        )

    mgr.assign_and_execute = AsyncMock(side_effect=mock_assign_and_execute)
    return mgr


class TestEndToEndPipeline:
    """End-to-End integration test suite for full autonomous content pipeline."""

    @pytest.mark.asyncio
    async def test_e2e_full_pipeline_execution(
        self,
        sample_e2e_request: WorkflowRequest,
        integrated_workforce_manager: WorkforceManager,
        integration_tmp_dir: Path,
    ):
        bus = MessageBus()
        chk_mgr = CheckpointManager(storage_dir=integration_tmp_dir)
        engine = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=integrated_workforce_manager,
            bus=bus,
        )

        # Execute complete workflow request
        result = await engine.execute_workflow(sample_e2e_request)

        # Assertions
        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps_completed == 8
        assert result.error is None
        assert result.execution_time_sec > 0.0

        # PublicationPackage assertions
        assert result.publication_package is not None
        assert result.publication_package.platform == "linkedin"
        assert result.publication_package.final_url == "https://linkedin.com/post/e2e-123456"
        assert result.publication_package.publish_status == PublishStatus.PUBLISHED

        # Immutable lineage assertions
        assert result.verification_report is not None
        assert result.verification_report.claims_verified == 5
        assert result.quality_scores is not None
        assert result.quality_scores.readability_score == 0.92
        assert result.seo_scores is not None
        assert result.seo_scores.overall_seo_score == 0.95

        # Metrics summary assertions
        assert "total_execution_time_sec" in result.metrics_summary
        assert result.metrics_summary["success_rate"] == 1.0
        assert result.metrics_summary["checkpoint_count"] == 8
        assert result.metrics_summary["artifacts_generated_count"] > 0
