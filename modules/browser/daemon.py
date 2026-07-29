import logging
import os
from pathlib import Path

import psutil

logger = logging.getLogger("AIContentOS.BrowserDaemon")

class BrowserCleanupDaemon:
    STALE_LOCK_FILES: list[str] = [
        "SingletonLock",
        "SingletonCookie",
        "SingletonSocket",
        "DevToolsActivePort",
        "lockfile"
    ]

    @classmethod
    def cleanup_profile_locks(cls, profile_dir: Path):
        """Scans user profile directory and removes stale Chromium lock files."""
        if not profile_dir.exists():
            return

        logger.info(f"Cleaning stale browser locks in profile: {profile_dir}")
        for root, _, files in os.walk(profile_dir):
            for file_name in files:
                if file_name in cls.STALE_LOCK_FILES:
                    lock_path = Path(root) / file_name
                    try:
                        lock_path.unlink(missing_ok=True)
                        logger.debug(f"Removed stale lock file: {lock_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove lock file {lock_path}: {e}")

    @classmethod
    def kill_orphan_chromium_processes(cls):
        """Finds and terminates orphan Chromium/Chrome processes associated with automated profiles."""
        logger.info("Checking for orphan automated Chromium processes...")
        terminated_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (proc.info['name'] or '').lower()
                cmdline = ' '.join(proc.info['cmdline'] or [])

                # Identify headless or automated chrome instances launched by Playwright
                if ('chrome' in name or 'chromium' in name) and ('--disable-blink-features=AutomationControlled' in cmdline or 'user_data' in cmdline):
                    logger.warning(f"Terminating orphan Chromium process [PID: {proc.info['pid']}]")
                    proc.kill()
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        if terminated_count > 0:
            logger.info(f"Terminated {terminated_count} orphan browser process(es).")

    @classmethod
    def prepare_startup(cls, profile_dir: Path):
        """Executes full pre-launch cleanup routine."""
        cls.cleanup_profile_locks(profile_dir)

browser_daemon = BrowserCleanupDaemon()
