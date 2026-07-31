# Infrastructure Subsystem 🛡️

The Infrastructure subsystem handles production environment configuration (`AppConfig`), application bootstrap (`StartupManager`), readiness probes (`HealthChecker`), and container deployment manifests.

---

## 1. Purpose

Ensures secure, reproducible application bootstrapping, credential protection, health readiness reporting, and containerized deployment across development, staging, and production environments.

---

## 2. 5-Stage Startup Sequence Diagram

```mermaid
sequenceDiagram
    participant Main as Application Main
    participant Startup as StartupManager
    participant Config as AppConfig
    participant DB as SQLite DB
    participant Reg as SelectorRegistry
    participant Plugins as Research Plugins
    participant Obs as ObservabilitySubscriber

    Main->>Startup: bootstrap()
    Startup->>Config: Stage 1: Load Environment Settings
    Startup->>DB: Stage 2: Initialize SQLite DB Schemas (WAL Mode)
    Startup->>Reg: Stage 3: Load & Validate DOM Selectors (selectors.json)
    Startup->>Plugins: Stage 4: Register Research Plugins (Web, GitHub, Reddit, YouTube, Docs)
    Startup->>Obs: Stage 5: Bind Observability Event Subscribers
    Startup-->>Main: Return StartupReport(SUCCESS)
```

---

## 3. Container Deployment Architecture

```mermaid
graph TD
    subgraph Host Infrastructure
        LB[Reverse Proxy / Ingress]
    end

    subgraph Docker Container appuser:appgroup
        App[AI Content OS Process]
        Probe[HealthChecker /healthz]
        Prom[Metrics Endpoint /metrics]
        DBFile[(SQLite WAL Storage)]
    end

    LB --> App
    LB --> Probe
    LB --> Prom
    App --> DBFile
```

---

## 4. Core Components

- **`AppConfig`**: Strongly typed environment settings with `SecretStr` credential masking.
- **`StartupManager`**: Executes 5-stage bootstrap sequence and produces structured `StartupReport`.
- **`HealthChecker`**: Performs system readiness probes and returns strongly typed `HealthStatus`.

---

## 5. Security & Credentials

- **Non-Root System Execution**: Production Docker containers run as non-root user `appuser:appgroup` (uid 10001).
- **`SecretStr` Protection**: Masks credentials (`GEMINI_API_KEY`, etc.) from logs and string representations.

---

## 6. Related Components & References

- [System Architecture Overview](overview.md)
- [Observability Pipeline](observability.md)
