<!-- Repository Banner Placeholder -->
<p align="center">
  <img src="docs/assets/images/banner.png" alt="AI Content OS Banner" width="100%" />
</p>

# AI Content OS 🚀

<p align="center">
  <a href="https://github.com/mayank30-09/ai-content-os/actions/workflows/ci.yml"><img src="https://github.com/mayank30-09/ai-content-os/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os"><img src="https://img.shields.io/badge/tests-383%20passed-brightgreen.svg" alt="Tests" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os"><img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg" alt="Coverage" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.14%2B-blue.svg" alt="Python" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="docker/Dockerfile"><img src="https://img.shields.io/badge/docker-ready-blue.svg" alt="Docker" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os/releases"><img src="https://img.shields.io/github/v/release/mayank30-09/ai-content-os.svg" alt="Release" /></a>
  <br />
  <a href="https://github.com/mayank30-09/ai-content-os/stargazers"><img src="https://img.shields.io/github/stars/mayank30-09/ai-content-os?style=flat&logo=github" alt="GitHub Stars" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os/network/members"><img src="https://img.shields.io/github/forks/mayank30-09/ai-content-os?style=flat&logo=github" alt="GitHub Forks" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os/issues"><img src="https://img.shields.io/github/issues/mayank30-09/ai-content-os" alt="GitHub Issues" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" /></a>
  <a href="https://github.com/mayank30-09/ai-content-os/commits/main"><img src="https://img.shields.io/github/last-commit/mayank30-09/ai-content-os" alt="Last Commit" /></a>
</p>

---

## ❓ Why AI Content OS?

### The Problem
Traditional AI content generation scripts produce low-quality, single-prompt text riddled with factual hallucinations, poor formatting, unverified claims, and zero publishing capabilities. Developers building enterprise media automation lack a structured framework to coordinate research, memory, quality scoring, SEO, and multi-platform distribution.

### Who It Is Built For
AI Content OS is built for **Engineering Teams, AI Developers, Content Operations Leaders, and Media Organizations** who require production-ready, fault-tolerant AI pipelines capable of operating autonomously at scale.

### Key Differentiators
- **Modular Workforce Architecture**: 8 specialized AI workers operating in isolated, testable single-responsibility layers.
- **Strongly-Typed Lineage**: Immutable records (`VerificationReport`, `EditQualityScores`, `SEOScores`) preserved across DAG steps.
- **Zero-Data-Loss Crash Recovery**: `CheckpointManager` auto-saves step state; process crashes resume mid-pipeline without re-running earlier steps.
- **Enterprise Observability**: Built-in distributed tracing, latency percentile math (p95), and scrapable Prometheus `/metrics`.

---

## 📊 Project Statistics

- 🤖 **8 Production AI Workers** (`Research`, `Memory`, `Content Strategist`, `Writer`, `Fact Checker`, `Editor`, `SEO`, `Publisher`)
- ⚡ **DAG Workflow Engine** with topological execution and template support
- 💾 **Atomic Checkpoint & Crash Resume** (`CheckpointManager`)
- 📊 **Distributed Observability** (Prometheus & OpenTelemetry exporters)
- 🚀 **CI/CD Deployment Pipeline** with GitHub Actions & Docker Buildx
- 🐋 **Docker Ready** (Multi-stage non-root container image)
- ✅ **383+ Automated Unit & Integration Tests** (100% pass rate)
- 🧹 **Ruff Clean** (Strict linting & formatting compliance)
- 🏗️ **Production-Ready Architecture** (Enterprise configuration, `SecretStr` security, `/healthz` probes)

---

## 🖼️ Media & Showcase

> *Screenshots and demo recordings reserved in `showcase/` and `docs/assets/images/`.*

- **Demo GIF**: *(Placeholder: `docs/assets/images/demo.gif`)*
- **Terminal Execution**: *(Placeholder: `docs/assets/images/terminal.gif`)*
- **Architecture Diagram Exports**: *(Placeholder: `docs/assets/diagrams/system_architecture.png`)*

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    Req[WorkflowRequest] --> Engine[WorkflowEngine]
    Engine --> Planner[ExecutionPlanner DAG]
    Planner --> W1[Research Worker]
    W1 --> W2[Memory Worker]
    W2 --> W3[Content Strategist]
    W3 --> W4[Writer Worker]
    W4 --> W5[Fact Checker]
    W5 --> W6[Editor Worker]
    W6 --> W7[SEO Worker]
    W7 --> W8[Publisher Worker]
    W8 --> Package[PublicationPackage]
    Engine --> Obs[ObservabilityManager]
    Engine --> Chk[CheckpointManager]
```

---

## ⚡ Quickstart

```bash
# 1. Clone repository & install dependencies
git clone https://github.com/mayank30-09/ai-content-os.git
cd "ai-content-os"
uv sync

# 2. Set API credentials
export GEMINI_API_KEY="your_api_key_here"

# 3. Run full test suite (383 passing tests)
uv run pytest
```

---

## 🌐 Compatibility Matrix

| Platform / Tool | Version / Support | Status |
| :--- | :--- | :--- |
| **Python** | 3.14+ | ✅ Fully Supported |
| **uv** | 0.5.0+ | ✅ Primary Package Manager |
| **Docker** | 24.0+ / Compose v2 | ✅ Containerized Production |
| **Linux (Ubuntu/Debian)** | x86_64 / arm64 | ✅ Production Native |
| **macOS** | Apple Silicon / Intel | ✅ Verified |
| **Windows** | Windows 11 / WSL2 | ✅ Verified |

---

## 📚 Documentation Map

- [5-Minute Quickstart Guide](docs/quickstart.md)
- [Installation Guide](docs/installation.md)
- [Architecture Overview](docs/architecture/overview.md)
- [AI Workforce Architecture](docs/architecture/workforce.md)
- [Workflow Engine & Checkpoints](docs/architecture/workflow_engine.md)
- [Observability & Monitoring](docs/architecture/observability.md)
- [Developer Contribution Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Community Support Guide](SUPPORT.md)

---

## 📜 License

Licensed under the [Apache 2.0 License](LICENSE).
