# AI Content OS Documentation Map 🗺️

Welcome to the official documentation for **AI Content OS**, an enterprise-grade autonomous AI workforce and pipeline orchestration engine for end-to-end content research, generation, fact-checking, editing, SEO optimization, and multi-platform publishing.

---

## 🚀 Getting Started

- **[5-Minute Quickstart](quickstart.md)**: Get up and running in 5 minutes with `uv` and your Gemini API key.
- **[Installation Guide](installation.md)**: Complete setup instructions for local development (`uv`), Docker containers, Docker Compose, and systemd deployment.

---

## 🏗️ Core Architecture & Subsystems

- **[Architecture Overview](architecture/overview.md)**: High-level system architecture and component interaction model.
- **[AI Workforce Subsystem](architecture/workforce.md)**: Topology of `WorkforceManager` and the 8 specialized production AI workers.
- **[Workflow Engine Subsystem](architecture/workflow_engine.md)**: DAG execution planning, `ArtifactRegistry` type validation, atomic `CheckpointManager`, and `RetryManager`.
- **[Memory Subsystem](architecture/memory_system.md)**: Intelligent SQLite `MemoryStore` for institutional context and query resolution.
- **[Observability Subsystem](architecture/observability.md)**: `ObservabilityManager`, distributed tracing, p95 latency histograms, audit logging, and Prometheus/OTel exporters.
- **[Infrastructure Subsystem](architecture/infrastructure.md)**: `AppConfig`, `SecretStr` security, 5-stage `StartupManager`, and `/healthz` readiness probes.

---

## 📚 Guides, Resources & Community

- **[Examples Index](examples.md)**: Runnable python script examples for custom workers, custom templates, and observability exports.
- **[Troubleshooting Guide](troubleshooting.md)**: Diagnostic guide for Gemini API, SQLite, Docker, and checkpoint recovery issues.
- **[Frequently Asked Questions (FAQ)](faq.md)**: Common technical and architectural questions answered.
- **[Project Roadmap](roadmap.md)**: Strategic development milestones and future feature roadmap.
- **[Developer Contribution Guide](contributing.md)**: Contribution guidelines, code standards, and PR workflows.

---

## ➡️ Next Reading

Ready to run your first workflow? Head over to the **[5-Minute Quickstart Guide](quickstart.md)**!
