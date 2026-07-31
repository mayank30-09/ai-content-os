#!/usr/bin/env bash
# Post-deployment Health Readiness Probe Script for AI Content OS
set -euo pipefail

echo "[HEALTH] Auditing application readiness..."
python -c "
from modules.config import get_config
from modules.infrastructure import HealthChecker
h = HealthChecker(get_config())
status = h.check_readiness()
print(f'[HEALTH] Readiness Status: {status.status.value}')
assert status.status.value != 'UNHEALTHY', 'Application readiness check failed'
"
echo "[HEALTH] Health probe PASSED cleanly."
