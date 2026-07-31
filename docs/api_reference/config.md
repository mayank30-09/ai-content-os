# API Reference: Configuration Subsystem (`modules.config`)

The Configuration subsystem manages environment-specific settings, AI provider parameters, database targets, logging levels, and feature flags.

---

## `AppConfig`

```python
from modules.config import AppConfig, get_config

config: AppConfig = get_config()
```

### Fields

| Field Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `config_version` | `str` | `"v0.8.3"` | Active configuration version identifier. |
| `env` | `EnvironmentConfig` | Dev/Prod settings | Active environment configuration instance. |
| `worker` | `WorkerConfig` | Worker limits | Worker execution timeouts and retry limits. |
| `ai_provider` | `AIProviderConfig` | Gemini settings | Active AI provider configuration. |
| `publisher` | `PublisherConfig` | Credentials | Multi-platform publisher credentials (`SecretStr`). |
| `database` | `DatabaseConfig` | SQLite settings | SQLite database path and WAL mode toggle. |
| `logging` | `LoggingConfig` | Loguru settings | Log level, formatting, and file targets. |
| `feature_flags` | `FeatureFlags` | Flags | Toggles for async message bus, tracing, etc. |

---

## `AIProviderConfig`

| Field Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `provider` | `str` | `"gemini"` | Active AI provider name. |
| `model_name` | `str` | `"gemini-2.5-flash"` | Primary Gemini model ID. |
| `api_key` | `SecretStr` | Envar `GEMINI_API_KEY` | Masked Gemini API key. |
| `temperature` | `float` | `0.7` | Sampling temperature (0.0 – 1.0). |

---

## ➡️ Next Reading

Read the **[Workforce API Reference](workforce.md)** or **[Workflow API Reference](workflow.md)**.
