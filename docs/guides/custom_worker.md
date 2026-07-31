# Developer Guide: Building Custom AI Workers 🛠️

This guide walks you through implementing a custom production AI worker (e.g. a Translation Worker) and integrating it with `WorkforceManager`.

---

## Step 1: Define Output Pydantic Model

Define your worker's output artifact schema using Pydantic v2:

```python
from pydantic import BaseModel, Field

class TranslationData(BaseModel):
    target_language: str
    translated_title: str
    translated_content: str
    quality_score: float = Field(default=0.95, ge=0.0, le=1.0)
```

---

## Step 2: Implement Custom Worker Class

Inherit from `BaseWorker` and implement the `execute` method:

```python
from modules.workforce.base_worker import BaseWorker
from modules.workflow.models import WorkflowContext, TaskResult

class TranslationWorker(BaseWorker):
    def __init__(self, config=None):
        super().__init__(worker_id="translation_worker", config=config)

    async def execute(self, context: WorkflowContext) -> TaskResult:
        # Retrieve previous step output typed from ArtifactRegistry
        writer_output = context.artifacts.get_typed("draft_content", BaseModel)
        
        # Perform translation logic
        translation = TranslationData(
            target_language="spanish",
            translated_title="Agentes de IA Autónomos",
            translated_content="Contenido traducido al español...",
            quality_score=0.98
        )
        
        # Save output into ArtifactRegistry
        context.artifacts.set("translation_data", translation)
        
        return TaskResult(
            task_id="task_translation_001",
            status="SUCCESS",
            output_artifacts={"translation_data": translation.model_dump()}
        )
```

---

## Step 3: Register Worker with WorkforceManager

```python
workforce_manager.register_worker("translation_worker", TranslationWorker(config=config))
```

---

## ➡️ Next Reading

Learn how to build custom workflow DAG topologies in the **[Custom Workflow Guide](custom_workflow.md)**.
