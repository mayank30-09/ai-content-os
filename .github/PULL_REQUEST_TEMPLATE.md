# Pull Request Checklist

Thank you for your pull request! Please review the checklist below to ensure a smooth review process.

---

## 📝 Summary

Provide a concise description of the changes made and the issue/feature being addressed.

Fixes #(issue_number)

---

## ⚙️ Type of Change

- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix/feature causing existing functionality to change)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring or performance improvement

---

## 🧪 Verification & Testing

Describe the tests you ran to verify your changes:

- [ ] Executed full pytest suite (`uv run pytest`) — all 383+ tests passing.
- [ ] Ran Ruff linter (`uv run ruff check .`) — zero warnings/errors.
- [ ] Added new unit/integration tests covering new functionality.

---

## 🛡️ Checklist

- [ ] My code follows the style guidelines of this project (Python 3.14+, Google-style docstrings).
- [ ] I have performed a self-review of my own code.
- [ ] I have commented my code, particularly in hard-to-understand areas.
- [ ] I have updated the documentation accordingly.
- [ ] My changes generate no new warnings or lint errors.
- [ ] No hardcoded secrets or credentials are introduced.
