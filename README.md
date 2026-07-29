# AI Content OS 🚀

A modular, local-first content intelligence and automated publishing workspace built with Python 3.11+, FastAPI, SQLite, and Playwright browser automation.

## Key Principles

- **Local-First**: All research, generation logs, persistent browser profiles, and SQLite data remain strictly local on your machine.
- **Zero Paid API Fees**: Leverages browser automation with subscription-based web interfaces (Google Gemini Pro) instead of paid API tokens.
- **Hardened Human Approval Gate**: Structural invariant ensuring no content is published online without explicit human review and authorization.
- **Hexagonal Architecture**: Decoupled domain models, ports, and adapters for AI providers, research engines, and publishing platforms.

## Prerequisites

- **Python**: 3.11 or higher (3.13 recommended)
- **Package Manager**: `uv` or standard `pip`
- **OS**: Windows 11 / Linux / macOS

## Quick Start Guide

### 1. Installation using `uv` (Recommended)

```powershell
# Create virtual environment and install dependencies
uv venv
.venv\Scripts\activate
uv pip install -e .[dev]

# Install Playwright browser binaries
python -m playwright install chromium
```

### 2. Alternative Installation using `pip`

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Running the Server

```powershell
python main.py
```

Access the interactive Dashboard at `http://127.0.0.1:8000`.

## Testing & Code Quality

```powershell
# Run unit tests
python -m pytest tests/

# Run linter
ruff check .
```
