# Changelog

All notable changes to the AI Content OS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.8.3] - 2026-07-31

### Added
- **Production CI/CD Pipeline**: GitHub Actions workflows for linting, pytest matrix, container build, security scans, and semantic release.
- **Production Observability Subsystem**: `ObservabilityManager` facade with distributed tracing, latency histograms (p95 math), audit logging, and Prometheus/OTel exporters.
- **Production Infrastructure & Config**: `AppConfig`, `StartupManager` 5-stage bootstrap, `HealthChecker` readiness probes, and multi-environment settings templates.
- **End-to-End Pipeline Integration**: Full 8-worker integration test suite verifying workflow execution from request to publication.

## [v0.7.4] - 2026-07-30

### Added
- **Workflow Engine Subsystem**: `WorkflowEngine`, DAG execution planner, `ArtifactRegistry` type validation, `CheckpointManager`, and `RetryManager`.

## [v0.6.8] - 2026-07-28

### Added
- **Production Publisher Worker**: Preparing platform payloads, resolving link placeholders, and publishing content.
- **Production SEO Worker**: SEO keyword density analysis, meta title/description generation, and schema template population.

## [v0.5.0] - 2026-07-25

### Added
- **Production Editor Worker & Fact Checker Worker**: Quality scoring, claim verification, and draft refinement.

## [v0.1.0] - 2026-07-20

### Added
- Initial release of AI Content OS Core Workforce Architecture.
