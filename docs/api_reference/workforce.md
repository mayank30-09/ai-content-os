# API Reference: Workforce Subsystem (`modules.workforce`)

The Workforce subsystem manages specialized production AI workers under `WorkforceManager`.

---

## `WorkforceManager`

```python
from modules.workforce import WorkforceManager

manager = WorkforceManager(config=config)
```

### Methods

#### `get_worker(worker_id: str) -> BaseWorker`
Retrieves a worker instance by string ID.

#### `execute_worker(worker_id: str, context: WorkflowContext) -> TaskResult`
Executes a single worker step asynchronously and returns a `TaskResult`.

---

## `BaseWorker`

Abstract base class for all production workers.

```python
class BaseWorker(ABC):
    @abstractmethod
    async def execute(self, context: WorkflowContext) -> TaskResult:
        """Executes worker logic and returns a TaskResult with output artifacts."""
        pass
```

---

## `TaskResult`

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `task_id` | `str` | Unique execution task ID. |
| `status` | `str` | `"SUCCESS"`, `"FAILED"`, or `"RETRYing"`. |
| `output_artifacts` | `dict[str, Any]` | Dictionary of produced output artifacts. |
| `error_message` | `Optional[str]` | Failure error message if status is FAILED. |

---

## ➡️ Next Reading

Read the **[Workflow API Reference](workflow.md)** or **[Custom Worker Guide](../guides/custom_worker.md)**.
