"""Workflow Context module for Workflow Engine subsystem.

Manages pipeline state, artifact propagation via ArtifactRegistry,
and task construction for worker dispatch.
"""

from typing import Any

from loguru import logger

from modules.workflow.artifact_registry import ArtifactRegistry
from modules.workflow.models import WorkflowRequest, WorkflowStep
from modules.workforce.models import Task, TaskPriority


class WorkflowContext:
    """Pipeline execution context managing artifacts and worker task construction.

    Uses an embedded ``ArtifactRegistry`` to maintain strongly-typed artifact state
    across workflow steps.
    """

    def __init__(
        self,
        request: WorkflowRequest,
        workflow_id: str,
        initial_registry: ArtifactRegistry | None = None,
    ) -> None:
        """Initializes WorkflowContext with user request and workflow ID.

        Args:
            request: WorkflowRequest instance.
            workflow_id: Unique workflow execution ID.
            initial_registry: Optional pre-populated ArtifactRegistry.
        """
        self.request: WorkflowRequest = request
        self.workflow_id: str = workflow_id
        self.artifacts: ArtifactRegistry = initial_registry or ArtifactRegistry()
        self.step_outputs: dict[str, Any] = {}

    def store_artifact(self, key: str, artifact: Any) -> None:
        """Stores a generated artifact into the ArtifactRegistry.

        Args:
            key: Artifact identifier key.
            artifact: Artifact model or dict.
        """
        self.artifacts.register(key, artifact)

    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Retrieves an artifact from the ArtifactRegistry.

        Args:
            key: Artifact identifier key.
            default: Default value if key is not found.

        Returns:
            Artifact object or default value.
        """
        return self.artifacts.get(key, default)

    def build_worker_task(self, step: WorkflowStep) -> Task:
        """Assembles a workforce Task object for the given WorkflowStep.

        Gathers required input artifacts from the ArtifactRegistry and packages
        them into task.payload alongside workflow request context parameters.

        Args:
            step: WorkflowStep to construct Task for.

        Returns:
            Task specification ready for WorkforceManager dispatch.
        """
        payload: dict[str, Any] = {
            "topic": self.request.topic,
            "query": self.request.topic,
            "keywords": self.request.keywords,
            "platform": self.request.target_platform,
            "content_format": self.request.content_format,
            "audience": self.request.audience,
            "objective": self.request.objective,
            "writing_style": self.request.writing_style,
            "route_map": self.request.route_map,
            "base_domain": self.request.base_domain,
            **self.request.context_overrides,
        }

        # Inject all required input artifacts from registry into payload
        for req_key in step.required_inputs:
            if self.artifacts.contains(req_key):
                payload[req_key] = self.artifacts.get(req_key)
            else:
                logger.warning(
                    f"WorkflowContext: step '{step.step_id}' required input artifact "
                    f"'{req_key}' not found in registry."
                )

        # Also inject all stored artifacts into payload for complete lineage access
        for key, val in self.artifacts.all_items().items():
            if key not in payload:
                payload[key] = val

        return Task(
            type=step.worker_type,
            creator=f"workflow_{self.workflow_id}",
            payload=payload,
            priority=TaskPriority.NORMAL,
        )
