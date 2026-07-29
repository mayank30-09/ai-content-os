"""Browser manager orchestrator module for AI Content OS.

High-level interface for managing browser automation subsystem lifecycle: start, stop, and restart.
"""

from pathlib import Path

from loguru import logger

from config.settings import settings
from modules.browser.daemon import browser_daemon
from modules.browser.pool import BrowserPool, browser_pool


class BrowserManager:
    """High-level lifecycle controller for the browser automation engine."""

    def __init__(self, pool: BrowserPool = browser_pool):
        self.pool = pool
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        """Returns current operational status of the browser manager."""
        return self._is_running

    async def start(
        self,
        user_data_dir: Path | None = None,
        headless: bool | None = None,
    ) -> None:
        """Starts the browser automation subsystem and pre-warms context.

        Args:
            user_data_dir: Profile directory path. Defaults to settings.GEMINI_PROFILE_DIR.
            headless: Override for headless execution.
        """
        profile_dir = user_data_dir or settings.GEMINI_PROFILE_DIR
        logger.info(f"Starting BrowserManager [Profile: '{profile_dir}']...")

        # Run pre-startup cleanup
        browser_daemon.prepare_startup(profile_dir)

        # Pre-warm persistent context
        await self.pool.get_context(user_data_dir=profile_dir, headless=headless)
        self._is_running = True
        logger.info("BrowserManager started successfully.")

    async def stop(self) -> None:
        """Gracefully shuts down active browser contexts and engine."""
        logger.info("Stopping BrowserManager...")
        await self.pool.close()
        self._is_running = False
        logger.info("BrowserManager stopped successfully.")

    async def restart(
        self,
        user_data_dir: Path | None = None,
        headless: bool | None = None,
    ) -> None:
        """Restarts the browser subsystem by stopping and re-initializing contexts."""
        logger.info("Restarting BrowserManager...")
        await self.stop()
        await self.start(user_data_dir=user_data_dir, headless=headless)
        logger.info("BrowserManager restarted successfully.")

browser_manager = BrowserManager()
