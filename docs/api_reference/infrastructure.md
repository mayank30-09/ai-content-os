# API Reference: Infrastructure Subsystem (`modules.infrastructure`)

Bootstrap management (`StartupManager`) and health readiness probes (`HealthChecker`).

---

## `StartupManager`

```python
from modules.infrastructure import StartupManager

startup = StartupManager(config=config)
report = startup.bootstrap()
```

### Methods

#### `bootstrap() -> StartupReport`
Executes the 5-stage application bootstrap sequence and returns a `StartupReport`.

---

## `HealthChecker`

```python
from modules.infrastructure import HealthChecker

checker = HealthChecker(config=config)
status: HealthStatus = checker.check_health()
```

### Methods

#### `check_health() -> HealthStatus`
Returns strongly typed `HealthStatus` containing readiness boolean, memory stats, and subsystem checks.

---

## ➡️ Next Reading

Read the **[Deployment Guide](../guides/deployment.md)**.
