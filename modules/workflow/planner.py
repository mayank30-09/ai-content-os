"""Planner module for Workflow Engine subsystem.

Constructs dependency graphs (DAG) and builds WorkflowExecution plans by
consuming WorkflowTemplate instances.
"""

from loguru import logger

from modules.workflow.models import (
    WorkflowExecution,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStep,
)
from modules.workflow.templates import (
    FastTrackPipelineTemplate,
    StandardContentPipelineTemplate,
    WorkflowTemplate,
)


class DependencyGraph:
    """Directed Acyclic Graph (DAG) validator and dependency order solver."""

    def __init__(self, steps: list[WorkflowStep]) -> None:
        """Initializes DependencyGraph with an ordered list of WorkflowStep objects.

        Args:
            steps: List of WorkflowStep objects.
        """
        self.steps: list[WorkflowStep] = steps

    def validate_dag(self) -> bool:
        """Validates that all step input dependencies are satisfied by prior step outputs.

        Returns:
            bool: True if DAG is valid and acyclic.

        Raises:
            ValueError: If a step requires an input artifact that is never produced by an earlier step.
        """
        produced_artifacts: set[str] = set()

        for step in self.steps:
            for req in step.required_inputs:
                if req not in produced_artifacts:
                    raise ValueError(
                        f"DependencyGraph validation error: step '{step.step_id}' requires input "
                        f"'{req}', which is not produced by any preceding step in the pipeline."
                    )
            produced_artifacts.add(step.output_artifact_key)

        return True

    def get_execution_order(self) -> list[WorkflowStep]:
        """Returns the topological execution order of steps.

        Returns:
            List of WorkflowStep objects.
        """
        return self.steps


class ExecutionPlanner:
    """Constructs WorkflowExecution plans by consuming WorkflowTemplate instances."""

    def __init__(self) -> None:
        self.templates: dict[str, WorkflowTemplate] = {}
        # Register default templates
        self.register_template(StandardContentPipelineTemplate())
        self.register_template(FastTrackPipelineTemplate())

    def register_template(self, template: WorkflowTemplate) -> None:
        """Registers a WorkflowTemplate instance.

        Args:
            template: WorkflowTemplate implementation.
        """
        self.templates[template.template_name] = template
        logger.debug(f"ExecutionPlanner registered template '{template.template_name}'")

    def build_plan(
        self,
        request: WorkflowRequest,
        workflow_id: str,
    ) -> WorkflowExecution:
        """Builds a validated WorkflowExecution plan from a WorkflowRequest.

        Args:
            request: WorkflowRequest specification.
            workflow_id: Unique workflow ID.

        Returns:
            Validated WorkflowExecution instance.

        Raises:
            ValueError: If template_name is not registered or DAG validation fails.
        """
        template_name = request.template_name or "standard_content_pipeline"
        template = self.templates.get(template_name)

        if not template:
            raise ValueError(
                f"ExecutionPlanner: template '{template_name}' is not registered. "
                f"Available templates: {list(self.templates.keys())}"
            )

        steps = template.build_steps(request)
        graph = DependencyGraph(steps)
        graph.validate_dag()

        logger.info(
            f"ExecutionPlanner: built plan for workflow '{workflow_id}' "
            f"using template '{template_name}' ({len(steps)} steps)."
        )

        return WorkflowExecution(
            workflow_id=workflow_id,
            template_name=template_name,
            status=WorkflowStatus.PENDING,
            steps=steps,
            current_step_index=0,
        )
