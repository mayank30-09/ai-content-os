# System Design: AI Content OS

## Architectural Blueprint

### Layered Subsystem Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Workflow Engine Layer                           │
│  (WorkflowEngine, ExecutionPlanner, ArtifactRegistry, CheckpointManager)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                        AI Workforce Core Layer                         │
│  (WorkforceManager, BaseWorker, 8 Production Workers, MessageBus)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Infrastructure & Observability Layer                │
│  (AppConfig, StartupManager, HealthChecker, ObservabilityManager)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Trade-offs & Design Decisions

### 1. In-Memory Event Bus vs. Distributed Queue (Kafka/RabbitMQ)
- **Decision**: In-memory `MessageBus` with async task queues for initial deployment, backed by pluggable workforce events.
- **Rationale**: Keeps worker execution ultra-fast (<50ms latency overhead) while preserving clear abstraction boundaries for future Redis/RabbitMQ event broker integration.

### 2. Pydantic v2 BaseModels vs. Dataclasses
- **Decision**: Standardized on Pydantic v2 `BaseModel`.
- **Rationale**: Provides automatic JSON serialization, strict type validation, field constraints, and `SecretStr` credential masking.

### 3. Atomic JSON File Checkpointing vs. Relational State Tracking
- **Decision**: `CheckpointManager` disk auto-saving with JSON files per workflow execution ID.
- **Rationale**: Zero external database dependency for workflow resumption; allows instant crash recovery even if external services fail.
