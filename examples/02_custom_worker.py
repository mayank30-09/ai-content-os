"""Example 02: Custom AI Worker Implementation.

Demonstrates creating a custom worker subclassing BaseWorker with a Pydantic v2 output model.
"""

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from modules.config import get_config
from modules.workflow.models import TaskResult, WorkflowContext
from modules.workforce.base_worker import BaseWorker
from modules.workforce.manager import WorkforceManager


class TranslationData(BaseModel):
    """Pydantic v2 output model for custom TranslationWorker."""

    target_language: str
    translated_title: str
    translated_content: str
    quality_score: float = Field(default=0.98, ge=0.0, le=1.0)


class CustomTranslationWorker(BaseWorker):
    """Custom production worker performing content translation."""

    def __init__(self, config: Any = None) -> None:
        super().__init__(worker_id="custom_translation_worker", config=config)

    async def execute(self, context: WorkflowContext) -> TaskResult:
        """Executes custom translation logic."""
        translation = TranslationData(
            target_language="spanish",
            translated_title="Agentes de IA Autónomos",
            translated_content="Contenido traducido al español con alta precisión.",
            quality_score=0.99,
        )

        # Store output in strongly-typed ArtifactRegistry
        context.artifacts.set("translation_data", translation)

        return TaskResult(
            task_id="task_translation_001",
            status="SUCCESS",
            output_artifacts={"translation_data": translation.model_dump()},
        )


async def main() -> None:
    """Registers and tests the custom worker."""
    config = get_config()
    manager = WorkforceManager(config=config)

    worker = CustomTranslationWorker(config=config)
    manager.register_worker("custom_translation_worker", worker)

    print(f"✅ Registered custom worker: {worker.worker_id}")


if __name__ == "__main__":
    asyncio.run(main())
