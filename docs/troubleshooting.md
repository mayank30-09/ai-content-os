# Troubleshooting & Diagnostic Guide 🔍

This guide provides diagnostic procedures and resolution steps for common operational issues encountered in AI Content OS.

---

## 1. Configuration & Environment Issues

### Symptom: `ValidationError: Field required [type=missing_argument]`
- **Root Cause**: A required environment variable (e.g. `GEMINI_API_KEY`) is missing from `AppConfig`.
- **Resolution**: Ensure `.env` is populated or environment variable is exported:
  ```bash
  export GEMINI_API_KEY="your_api_key_here"
  ```

---

## 2. Gemini API & AI Provider Issues

### Symptom: `GeminiWebError: Session expired or invalid cookies`
- **Root Cause**: Web plugin cookies or session tokens expired during scraping/research.
- **Resolution**: Re-authenticate or update session credentials in `config/selectors.json`.

---

## 3. SQLite Database Issues

### Symptom: `sqlite3.OperationalError: database is locked`
- **Root Cause**: Concurrent write locks on SQLite database files.
- **Resolution**: Verify WAL mode is enabled (`PRAGMA journal_mode=WAL;`). AI Content OS automatically initializes SQLite DBs with WAL mode enabled (`WAL mode active`).

---

## 4. Checkpoint & Recovery Issues

### Symptom: Workflow resume fails after crash
- **Root Cause**: Corrupted or incomplete JSON file in `user_data/checkpoints/`.
- **Resolution**: Validate JSON syntax of `user_data/checkpoints/{workflow_id}.json`. If corrupted, delete the checkpoint file to trigger a fresh execution.

---

## 5. Docker & Container Issues

### Symptom: `Permission denied` inside container
- **Root Cause**: Non-root system user (`appuser`) lacking write access to `/app/user_data`.
- **Resolution**: Ensure host directory permissions match `uid 10001`:
  ```bash
  chown -R 10001:10001 ./user_data
  ```

---

## ➡️ Next Reading

Check the **[FAQ](faq.md)** for frequently asked questions or read the **[Observability Architecture](architecture/observability.md)**.
