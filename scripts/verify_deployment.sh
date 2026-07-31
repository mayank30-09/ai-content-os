#!/usr/bin/env bash
# Deployment Verification & Smoke Testing Script for AI Content OS
# Positioned between deployment and rollback to validate deployment health before rollback trigger.
set -euo pipefail

echo "[VERIFY] Running deployment verification & post-deployment smoke tests..."

# Step 1: Health Readiness Probe
python -c "
from modules.config import get_config
from modules.infrastructure import HealthChecker
h = HealthChecker(get_config())
res = h.check_readiness()
assert res.status.value != 'UNHEALTHY', 'Readiness probe failed'
" || {
    echo "[VERIFY] Readiness probe failed. Triggering rollback script..."
    chmod +x scripts/rollback.sh
    ./scripts/rollback.sh
    exit 1
}

# Step 2: Smoke Test Verification
python -c "
from modules.config import get_config
from modules.infrastructure import StartupManager
from modules.observability import ObservabilityManager

cfg = get_config()
mgr = StartupManager(cfg)
rep = mgr.run_startup_sequence()
assert rep.success, 'Startup smoke test failed'

obs = ObservabilityManager()
obs.record_counter('smoke_test_total', value=1.0)
summary = obs.get_telemetry_summary()
assert summary.total_metrics_recorded > 0, 'Observability telemetry smoke test failed'
print('[VERIFY] Smoke tests passed cleanly!')
" || {
    echo "[VERIFY] Smoke tests failed. Triggering rollback script..."
    chmod +x scripts/rollback.sh
    ./scripts/rollback.sh
    exit 1
}

echo "[VERIFY] Deployment verification completed successfully."
