# Workflow Engine Subsystem ⚡

The `WorkflowEngine` controls topological execution planning, artifact typing, atomic state saving, and crash recovery.

---

## 1. Purpose

Orchestrates the lifecycle of content workflows, enforcing DAG execution order, type-safe artifact propagation (`ArtifactRegistry`), transient retry policies (`RetryManager`), and zero-data-loss checkpoint recovery (`CheckpointManager`).

---

## 2. Workflow Engine Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Submitted: execute_workflow(request)
    Submitted --> Planning: ExecutionPlanner.plan()
    Planning --> RunningStep: Topological DAG Step
    RunningStep --> ValidatingArtifact: Worker Complete (TaskResult)
    ValidatingArtifact --> SavingCheckpoint: ArtifactRegistry.set()
    SavingCheckpoint --> RunningStep: Next Step Available
    SavingCheckpoint --> Completed: All Steps Done
    RunningStep --> Retrying: Step Failed (RetryManager)
    Retrying --> RunningStep: Backoff Delay Elapsed
    Retrying --> Failed: Max Retries Exceeded
    Completed --> [*]: Return WorkflowResult
    Failed --> [*]: Return WorkflowResult (FAILED)
```

---

## 3. Artifact Registry Data Flow

```mermaid
sequenceDiagram
    participant Engine as WorkflowEngine
    participant Reg as ArtifactRegistry
    participant Worker as BaseWorker
    participant Pydantic as Pydantic v2 Model

    Engine->>Worker: execute(context)
    Worker->>Pydantic: Instantiate Output Model (e.g. SEOScores)
    Worker->>Reg: set("seo_scores", model_instance)
    Reg->>Pydantic: Validate Schema
    Reg-->>Engine: Stored Typed Artifact
    Engine->>Reg: get_typed("seo_scores", SEOScores)
    Reg-->>Engine: Returns SEOScores Instance
```

---

## 4. Atomic Checkpoint & Crash Recovery Sequence

```mermaid
sequenceDiagram
    participant Engine as WorkflowEngine
    participant Worker as Production Worker
    participant Chk as CheckpointManager
    participant Disk as Disk Storage (.json)

    Engine->>Worker: Execute Step N
    Worker-->>Engine: TaskResult(SUCCESS)
    Engine->>Chk: save_checkpoint(workflow_id, context)
    Chk->>Disk: Write atomic JSON file
    Note over Engine, Disk: Process Crash / Power Failure
    Note over Engine, Disk: Server Restarts & Calls resume_workflow(id)
    Engine->>Chk: load_checkpoint(workflow_id)
    Chk->>Disk: Read atomic JSON
    Chk-->>Engine: Rehydrated WorkflowContext
    Engine->>Worker: Resume Execution at Step N+1
```

---

## 5. Design Decisions

- **Atomic JSON Checkpointing**: Saves full execution state snapshots to disk after every completed step (`user_data/checkpoints/{workflow_id}.json`).
- **Strongly Typed Registry**: `ArtifactRegistry` uses `get_typed(key, ModelClass)` to guarantee type safety between worker steps.

---

## 6. Trade-offs

- Disk I/O overhead on step completion vs. crash recovery safety (I/O latency is <5ms per step).

---

## 7. Related Components & References

- [System Architecture Overview](overview.md)
- [AI Workforce Architecture](workforce.md)
