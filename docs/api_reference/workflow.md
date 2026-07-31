# API Reference: Workflow Subsystem (`modules.workflow`)

The Workflow subsystem controls DAG execution, artifact typing, checkpointing, and retry policies.

---

## `WorkflowEngine`

```python
from modules.workflow import WorkflowEngine, WorkflowRequest

engine = WorkflowEngine(config=config)
```

### Methods

#### `execute_workflow(request: WorkflowRequest) -> WorkflowResult`
Submits and executes a workflow request from end-to-end.

#### `resume_workflow(workflow_id: str) -> WorkflowResult`
Re-hydrates execution state from a disk JSON checkpoint and resumes from the crash point.

---

## `ArtifactRegistry`

Encapsulates strongly-typed artifact storage.

```python
registry = context.artifacts
registry.set("seo_scores", seo_instance)
scores = registry.get_typed("seo_scores", SEOScores)
```

#### `get_typed(key: str, model_cls: Type[T]) -> T`
Retrieves and validates an artifact against a target Pydantic v2 `BaseModel` class.

---

## `CheckpointManager`

Atomic JSON state checkpoint persistence.

#### `save_checkpoint(workflow_id: str, context: WorkflowContext)`
Saves atomic JSON snapshot to `user_data/checkpoints/{workflow_id}.json`.

#### `load_checkpoint(workflow_id: str) -> Optional[WorkflowContext]`
Loads snapshot from disk for crash recovery.

---

## ➡️ Next Reading

Read the **[Observability API Reference](observability.md)** or **[Custom Workflow Guide](../guides/custom_workflow.md)**.
