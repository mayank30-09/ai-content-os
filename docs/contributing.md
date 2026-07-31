# Developer Contribution Guide 🤝

Thank you for contributing to **AI Content OS**!

---

## 🛠️ Environment Setup

```bash
# 1. Fork and clone repository
git clone https://github.com/your-username/ai-content-os.git
cd ai-content-os

# 2. Sync virtual environment with uv
uv sync

# 3. Verify pytest suite (383 passing tests)
uv run pytest
```

---

## 📏 Development Rules

1. **Python Version**: Python 3.14+
2. **Formatting & Linting**: Always run `uv run ruff check --fix .` before committing.
3. **Type Safety**: Use Pydantic v2 models and complete type annotations.
4. **Zero Production Regressions**: All 383+ pytest tests must pass without errors.
5. **No Production Modifications**: Do not alter locked production worker contracts without architectural justification.

---

## ➡️ Next Reading

See **[Examples Index](examples.md)** for example scripts.
