# System Architecture Overview 🏗️

AI Content OS is an enterprise-grade autonomous AI workforce and pipeline orchestration engine built on Python 3.14, Pydantic v2, Loguru, and SQLite.

---

## 1. Purpose

The System Architecture defines the component interaction model, abstraction boundaries, data flow pipelines, and resilience mechanics across the 5 core subsystems of AI Content OS. It ensures decoupled, strongly-typed execution from initial workflow request to final multi-platform publication.

---

## 2. Complete System Architecture

```mermaid
graph TD
    subgraph Client Layer
        Req[WorkflowRequest]
    end

    subgraph Infrastructure Layer
        Config[AppConfig / EnvironmentConfig]
        Startup[StartupManager]
        Health[HealthChecker]
    end

    subgraph Workflow Engine Layer
        Engine[WorkflowEngine]
        Planner[ExecutionPlanner DAG]
        Registry[ArtifactRegistry]
        Checkpoint[CheckpointManager]
        Retry[RetryManager]
    end

    subgraph AI Workforce Layer
        Manager[WorkforceManager]
        W1[Research Worker]
        W2[Memory Worker]
        W3[Content Strategist Worker]
        W4[Writer Worker]
        W5[Fact Checker Worker]
        W6[Editor Worker]
        W7[SEO Worker]
        W8[Publisher Worker]
        Bus[MessageBus]
    end

    subgraph Memory Layer
        MemStore[MemoryStore]
        DB[SQLite DB WAL Mode]
    end

    subgraph Observability Layer
        Obs[ObservabilityManager]
        Tracer[Distributed Tracer]
        Metrics[MetricsCollector]
        Audit[AuditLogger]
        Prom[Prometheus Exporter]
    end

    Startup --> Config
    Startup --> DB
    Startup --> Health
    Req --> Engine
    Engine --> Planner
    Engine --> Registry
    Engine --> Checkpoint
    Engine --> Retry
    Planner --> Manager
    Manager --> W1
    Manager --> W2
    Manager --> W3
    Manager --> W4
    Manager --> W5
    Manager --> W6
    Manager --> W7
    Manager --> W8
    W2 --> MemStore
    MemStore --> DB
    W1 & W2 & W3 & W4 & W5 & W6 & W7 & W8 --> Bus
    Bus --> Obs
    Obs --> Tracer
    Obs --> Metrics
    Obs --> Audit
    Metrics --> Prom
    W8 --> Package[PublicationPackage]
```

---

## 3. Configuration Hierarchy

```mermaid
graph TD
    AppConfig[AppConfig config_version=v0.8.3]
    AppConfig --> EnvConfig[EnvironmentConfig dev / staging / prod]
    AppConfig --> WorkerConfig[WorkerConfig timeouts / retries]
    AppConfig --> AIConfig[AIProviderConfig gemini-2.5-flash / pro]
    AppConfig --> PubConfig[PublisherConfig linkedin / twitter / cms]
    AppConfig --> DBConfig[DatabaseConfig SQLite WAL mode]
    AppConfig --> LogConfig[LoggingConfig Loguru level]
    AppConfig --> Flags[FeatureFlags async_bus / tracing_enabled]
```

---

## 4. Subsystem Responsibilities & Interactions

| Subsystem | Primary Class | Key Interactions |
| :--- | :--- | :--- |
| **Workflow Engine** | `WorkflowEngine` | Interacts with `WorkforceManager` to execute DAG steps, `ArtifactRegistry` for typed inputs/outputs, `CheckpointManager` for state persistence, and `RetryManager` for error recovery. |
| **AI Workforce** | `WorkforceManager` | Manages 8 specialized `BaseWorker` instances, emits events over `MessageBus`. |
| **Memory System** | `MemoryStore` | Provides SQLite query resolution for `MemoryWorker` with WAL mode concurrency. |
| **Observability** | `ObservabilityManager` | Subscribes asynchronously to `MessageBus` via `ObservabilitySubscriber` to generate spans, histograms (p95), and audit logs. |
| **Infrastructure** | `StartupManager` | Orchestrates 5-stage application bootstrap and registers readiness probes with `HealthChecker`. |

---

## 5. Design Decisions

- **Explicit Subsystem Decoupling**: Subsystems communicate strictly through typed interfaces (`WorkflowContext`, `ArtifactRegistry`, `MessageBus`), prohibiting direct cross-layer private state mutation.
- **Pydantic v2 Contract Enforcements**: All inputs, outputs, and configs inherit from `BaseModel`, guaranteeing strict schema validation.
- **In-Memory Event Bus with Async Dispatch**: System events are broadcast over `MessageBus` to keep worker execution overhead under 50ms.

---

## 6. Trade-offs

- **SQLite WAL Mode vs. External Postgres**: SQLite eliminates external infra dependencies for local/edge deployments; high-concurrency multi-node setups require future database driver abstraction.
- **In-Memory Event Bus vs. Kafka**: Keeps local latency minimal while requiring future queue adapter for multi-server fanout.

---

## 7. Failure Handling

- **Step Isolation**: Single worker failures trigger `RetryManager` exponential backoff without corrupting global application state.
- **Atomic Checkpointing**: Process crashes resume cleanly from disk JSON checkpoints (`user_data/checkpoints/`).

---

## 8. Scalability & Extension Points

- **Custom Workers**: Implement `BaseWorker` and register with `WorkforceManager`.
- **Custom Workflow Templates**: Register custom DAG topologies in `WorkflowTemplate` registry.

---

## 9. Related Components & References

- [AI Workforce Architecture](workforce.md)
- [Workflow Engine & Checkpoints](workflow_engine.md)
- [Memory Subsystem](memory_system.md)
- [Observability Pipeline](observability.md)
- [Infrastructure & Deployment](infrastructure.md)
