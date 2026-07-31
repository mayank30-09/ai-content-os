"""Comprehensive unit and integration test suite for Production Deployment Pipeline subsystem.

Tests cover:
- Deployment directory structure & GitHub Workflows configuration existence (ci.yml, cd.yml, release.yml, security.yml, docs.yml).
- Dependabot configuration (.github/dependabot.yml) and CODEOWNERS (.github/CODEOWNERS) formatting.
- Pre-commit configuration (.pre-commit-config.yaml) structure.
- Deployment scripts existence (deploy.sh, health_check.sh, verify_deployment.sh, rollback.sh).
- Deployment verification & smoke testing logic execution.
"""

from pathlib import Path

import yaml

from modules.config import get_config
from modules.infrastructure import HealthChecker, ProbeState, StartupManager
from modules.observability import ObservabilityManager


class TestDeploymentPipelineConfiguration:
    """Unit tests verifying deployment configuration files and workflows."""

    def test_github_workflows_exist(self):
        wf_dir = Path(".github/workflows")
        assert wf_dir.exists()
        assert (wf_dir / "ci.yml").exists()
        assert (wf_dir / "cd.yml").exists()
        assert (wf_dir / "release.yml").exists()
        assert (wf_dir / "security.yml").exists()
        assert (wf_dir / "docs.yml").exists()

    def test_dependabot_config_valid_yaml(self):
        dep_file = Path(".github/dependabot.yml")
        assert dep_file.exists()
        with open(dep_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["version"] == 2
        assert len(data["updates"]) >= 2

    def test_codeowners_file_exists(self):
        co_file = Path(".github/CODEOWNERS")
        assert co_file.exists()
        content = co_file.read_text(encoding="utf-8")
        assert "@mayank30-09" in content

    def test_pre_commit_config_valid_yaml(self):
        pc_file = Path(".pre-commit-config.yaml")
        assert pc_file.exists()
        with open(pc_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "repos" in data
        assert len(data["repos"]) >= 2

    def test_deployment_scripts_exist(self):
        scripts_dir = Path("scripts")
        assert scripts_dir.exists()
        assert (scripts_dir / "deploy.sh").exists()
        assert (scripts_dir / "health_check.sh").exists()
        assert (scripts_dir / "verify_deployment.sh").exists()
        assert (scripts_dir / "rollback.sh").exists()


class TestDeploymentVerificationAndSmokeTests:
    """Integration test suite for post-deployment verification and smoke test logic."""

    def test_health_readiness_probe_verification(self):
        cfg = get_config()
        checker = HealthChecker(cfg)
        status = checker.check_readiness()
        assert status.status in (ProbeState.HEALTHY, ProbeState.DEGRADED)

    def test_startup_smoke_test(self):
        cfg = get_config()
        mgr = StartupManager(cfg)
        report = mgr.run_startup_sequence()
        assert report.success is True

    def test_observability_smoke_test(self):
        obs = ObservabilityManager()
        obs.record_counter("smoke_test_count", value=1.0)
        summary = obs.get_telemetry_summary()
        assert summary.total_metrics_recorded > 0
