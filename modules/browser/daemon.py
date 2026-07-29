"""Browser startup cleanup daemon module for AI Content OS.

Cleans up stale Chromium lock files and terminates orphan Playwright browser processes
prior to starting new automation sessions.
"""

import os
from pathlib import Path

import psutil
from loguru import logger


class BrowserCleanupDaemon:
    """Daemon for inspecting and cleaning orphan browser processes and lock files."""

    STALE_LOCK_FILES: list[str] = [
        "SingletonLock",
        "SingletonCookie",
        "SingletonSocket",
        "DevToolsActivePort",
        "lockfile",
    ]

    @classmethod
    def cleanup_profile_locks(cls, profile_dir: Path) -> int:
        """Scans user profile directory and removes stale Chromium lock files.

        Args:
            profile_dir: Directory path of browser user profile.

        Returns:
            int: Count of removed lock files.
        """
        if not profile_dir.exists():
            return 0

        logger.info(f"Scanning profile directory for stale lock files: '{profile_dir}'")
        removed_count = 0
        for root, _, files in os.walk(profile_dir):
            for file_name in files:
                if file_name in cls.STALE_LOCK_FILES:
                    lock_path = Path(root) / file_name
                    try:
                        lock_path.unlink(missing_ok=True)
                        logger.debug(f"Removed stale lock file: '{lock_path}'")
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove lock file '{lock_path}': {e}")

        if removed_count > 0:
            logger.info(f"Cleaned {removed_count} stale lock file(s) from '{profile_dir}'.")
        return removed_count

    @classmethod
    def kill_orphan_chromium_processes(cls) -> int:
        """Terminates orphan Chromium processes launched by Playwright.

        Returns:
            int: Count of terminated orphan processes.
        """
        logger.info("Checking for orphan automated Chromium processes...")
        terminated_count = 0
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info["name"] or "").lower()
                cmdline = " ".join(proc.info["cmdline"] or [])

                # Match automated Chrome/Chromium processes created by automation
                if ("chrome" in name or "chromium" in name) and (
                    "--disable-blink-features=AutomationControlled" in cmdline
                    or "user_data" in cmdline
                ):
                    logger.warning(f"Terminating orphan Chromium process [PID: {proc.info['pid']}]")
                    proc.kill()
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if terminated_count > 0:
            logger.info(f"Terminated {terminated_count} orphan browser process(es).")
        else:
            logger.debug("No orphan Chromium processes found.")
        return terminated_count

    @classmethod
    def prepare_startup(cls, profile_dir: Path) -> bool:
        """Executes full pre-launch cleanup routine.

        Args:
            profile_dir: Directory path of browser user profile.

        Returns:
            bool: True if cleanup completed without critical errors.
        """
        try:
            cls.cleanup_profile_locks(profile_dir)
            cls.kill_orphan_chromium_processes()
            logger.info(f"Browser pre-startup verification completed for '{profile_dir}'.")
            return True
        except Exception as e:
            logger.error(f"Browser startup cleanup failed for '{profile_dir}': {e}")
            return False

browser_daemon = BrowserCleanupDaemon()
