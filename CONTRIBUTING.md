# Contributing to AI Content OS

First off, thank you for considering contributing to AI Content OS! It's contributions like yours that make AI Content OS a powerful open-source project.

---

## 🛠️ Local Development Setup

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/ai-content-os.git
   cd ai-content-os
   ```

2. **Install Dependencies via `uv`**:
   ```bash
   uv sync
   ```

3. **Install Pre-Commit Hooks**:
   ```bash
   uv run pre-commit install
   ```

4. **Verify Your Environment**:
   ```bash
   uv run pytest
   ```

---

## 📐 Coding Standards & Guidelines

- **Python Version**: Python 3.14+
- **Code Style & Formatting**: Formatted cleanly with `ruff` (`uv run ruff check --fix .` and `uv run ruff format .`).
- **Type Hints**: Complete type annotations on all function signatures (`def fn(x: str) -> int:`).
- **Docstrings**: Google-style docstrings on all public classes, methods, and modules.
- **Testing**: Every new feature or bug fix MUST include unit/integration tests under `tests/`.

---

## 🔄 Pull Request Workflow

1. Create a descriptive topic branch: `git checkout -b feat/add-custom-worker`.
2. Commit your changes using Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
3. Ensure all quality gates pass:
   ```bash
   uv run ruff check .
   uv run pytest
   ```
4. Push your branch and open a Pull Request against `main`.
5. Complete the PR template checklist.
