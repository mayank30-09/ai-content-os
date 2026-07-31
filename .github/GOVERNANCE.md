# Repository Governance & Workflow Specification

This document defines the open-source community governance, issue triage process, label classification, pull request review lifecycle, and branching strategy for AI Content OS.

---

## 🏷️ Standard Issue Labels

All repository issues and pull requests are classified using standard labels:

| Label | Description | Color |
| :--- | :--- | :--- |
| `bug` | Unexpected error, crash, or contract violation | `#d73a4a` (Red) |
| `enhancement` | New feature or system capability request | `#a2eeef` (Cyan) |
| `documentation` | Documentation updates, guides, or docstring fixes | `#0075ca` (Blue) |
| `good first issue` | Good for newcomers to start contributing | `#7057ff` (Purple) |
| `help wanted` | Open issue seeking community contributions | `#008672` (Teal) |
| `security` | Security vulnerability, SAST finding, or patch | `#b60205` (Dark Red) |
| `performance` | Performance optimization or memory tuning | `#d4c5f9` (Lavender) |
| `question` | Inquiry regarding architecture or usage | `#d8d8d8` (Gray) |

---

## 🌿 Branching Strategy

- **`main`**: Production-ready branch. All commits must pass CI/CD workflows, 100% tests, and Ruff checks.
- **Topic Branches**:
  - Features: `feat/feature-name`
  - Fixes: `fix/bug-description`
  - Docs: `docs/topic-name`
  - Releases: `release/vX.Y.Z`

---

## 🔄 Issue & Pull Request Lifecycle

1. **Issue Creation**: User opens issue using modern GitHub Forms (`bug_report.yml` or `feature_request.yml`).
2. **Maintainer Triage**: Maintainer assigns standard labels and sets priority.
3. **Branch & Development**: Contributor creates a topic branch from `main`.
4. **Automated CI Validation**: GitHub Actions runs Ruff linting, Pytest suite, and security scans.
5. **Code Review**: At least one maintainer review is required before merging.
6. **Squash and Merge**: PR is merged into `main` using squash commits adhering to Conventional Commits format.

---

## 👥 Maintainer Responsibilities

- Respond to issue submissions and PRs within 48 hours.
- Maintain test coverage (100% test pass rate enforcement).
- Ensure strict adherence to non-breaking change policies.
- Keep dependencies updated via Dependabot.
