"""Workflow Templates module for Workflow Engine subsystem.

Defines the WorkflowTemplate abstraction and concrete pipeline templates
(StandardContentPipeline, FastTrackPipeline, CustomPipeline) consumed by the ExecutionPlanner.
"""

from abc import ABC, abstractmethod

from modules.workflow.models import RetryPolicy, WorkflowRequest, WorkflowStep


class WorkflowTemplate(ABC):
    """Abstract interface for workflow DAG templates."""

    @property
    @abstractmethod
    def template_name(self) -> str:
        """Template unique identifier name."""
        pass

    @abstractmethod
    def build_steps(self, request: WorkflowRequest) -> list[WorkflowStep]:
        """Builds an ordered list of WorkflowStep objects for this template.

        Args:
            request: User WorkflowRequest instance.

        Returns:
            List of WorkflowStep objects.
        """
        pass


class StandardContentPipelineTemplate(WorkflowTemplate):
    """Full 8-worker production AI content pipeline template.

    Pipeline Order:
        1. Research Worker          → research_package
        2. Memory Worker            → context_package
        3. Content Strategist       → strategy_package
        4. Writer Worker            → draft_package
        5. Fact Checker Worker      → verified_draft_package
        6. Editor Worker            → edited_draft_package
        7. SEO Worker               → seo_optimized_package
        8. Publisher Worker         → publication_package
    """

    @property
    def template_name(self) -> str:
        return "standard_content_pipeline"

    def build_steps(self, request: WorkflowRequest) -> list[WorkflowStep]:
        default_policy = RetryPolicy(max_retries=3, initial_delay_sec=0.1)

        return [
            WorkflowStep(
                step_id="step_01_research",
                worker_type="research_worker",
                description="Conduct deep web research and extract raw facts",
                required_inputs=[],
                output_artifact_key="research_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_02_memory",
                worker_type="memory_worker",
                description="Retrieve institutional knowledge and memory context",
                required_inputs=["research_package"],
                output_artifact_key="context_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_03_strategist",
                worker_type="strategist_worker",
                description="Formulate editorial strategy, outline, and target structure",
                required_inputs=["research_package", "context_package"],
                output_artifact_key="strategy_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_04_writer",
                worker_type="writer_worker",
                description="Generate complete initial content draft",
                required_inputs=["strategy_package", "context_package"],
                output_artifact_key="draft_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_05_fact_checker",
                worker_type="fact_checker_worker",
                description="Verify factual claims against research and context",
                required_inputs=["draft_package", "research_package", "context_package"],
                output_artifact_key="verified_draft_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_06_editor",
                worker_type="editor_worker",
                description="Edit content for readability, flow, grammar, and tone",
                required_inputs=["verified_draft_package"],
                output_artifact_key="edited_draft_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_07_seo",
                worker_type="seo_worker",
                description="Optimize headings, meta tags, schema, and keywords for SEO",
                required_inputs=["edited_draft_package"],
                output_artifact_key="seo_optimized_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_08_publisher",
                worker_type="publisher_worker",
                description="Resolve links, populate schema, build payload, and publish",
                required_inputs=["seo_optimized_package"],
                output_artifact_key="publication_package",
                retry_policy=default_policy,
            ),
        ]


class FastTrackPipelineTemplate(WorkflowTemplate):
    """Accelerated 4-worker pipeline template (Writer → Editor → SEO → Publisher)."""

    @property
    def template_name(self) -> str:
        return "fast_track_pipeline"

    def build_steps(self, request: WorkflowRequest) -> list[WorkflowStep]:
        default_policy = RetryPolicy(max_retries=2, initial_delay_sec=0.1)

        return [
            WorkflowStep(
                step_id="step_01_writer",
                worker_type="writer_worker",
                description="Generate content draft",
                required_inputs=[],
                output_artifact_key="draft_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_02_editor",
                worker_type="editor_worker",
                description="Edit draft",
                required_inputs=["draft_package"],
                output_artifact_key="edited_draft_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_03_seo",
                worker_type="seo_worker",
                description="SEO optimization",
                required_inputs=["edited_draft_package"],
                output_artifact_key="seo_optimized_package",
                retry_policy=default_policy,
            ),
            WorkflowStep(
                step_id="step_04_publisher",
                worker_type="publisher_worker",
                description="Publish content",
                required_inputs=["seo_optimized_package"],
                output_artifact_key="publication_package",
                retry_policy=default_policy,
            ),
        ]
