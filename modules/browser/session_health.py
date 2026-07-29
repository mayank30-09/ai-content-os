"""Session health manager module for AI Content OS.

Verifies authentication health for target web applications (Gemini, LinkedIn, X/Twitter),
detects expired session states, and manages headed manual login recovery sessions.
"""

from enum import Enum
from typing import Any

from loguru import logger

from config.settings import settings
from modules.browser.selector_manager import selector_registry


class SessionStatus(Enum):
    """Enumeration of session health states."""
    HEALTHY = "HEALTHY"
    EXPIRED = "EXPIRED"
    DEGRADED = "DEGRADED"

class SessionHealthManager:
    """Verifies session cookies/profiles and triggers manual login recovery if expired."""

    def __init__(self):
        self._statuses: dict[str, SessionStatus] = {
            "gemini_web": SessionStatus.EXPIRED,
            "linkedin": SessionStatus.EXPIRED,
            "x_twitter": SessionStatus.EXPIRED,
        }

    def get_status(self, platform: str) -> SessionStatus:
        """Returns current cached status for a platform."""
        return self._statuses.get(platform, SessionStatus.EXPIRED)

    async def verify_session(self, page: Any, platform: str) -> SessionStatus:
        """Verifies session health for a given platform page.

        Args:
            page: Active Playwright Page instance.
            platform: Platform identifier (e.g., 'gemini_web', 'linkedin', 'x_twitter').

        Returns:
            SessionStatus: HEALTHY if session inputs are accessible, EXPIRED or DEGRADED otherwise.
        """
        logger.info(f"Verifying authentication session health for platform: '{platform}'")
        try:
            if platform == "gemini_web":
                await page.goto(settings.GEMINI_WEB_URL, timeout=20000)
                try:
                    elem = await selector_registry.find_element(page, "gemini_web", "prompt_textarea")
                    if elem:
                        self._statuses[platform] = SessionStatus.HEALTHY
                        logger.info(f"Session HEALTHY for platform: '{platform}'")
                        return SessionStatus.HEALTHY
                except Exception:
                    pass

            elif platform == "linkedin":
                await page.goto(settings.LINKEDIN_WEB_URL, timeout=20000)
                try:
                    elem = await selector_registry.find_element(page, "linkedin_web", "start_post_button")
                    if elem:
                        self._statuses[platform] = SessionStatus.HEALTHY
                        logger.info(f"Session HEALTHY for platform: '{platform}'")
                        return SessionStatus.HEALTHY
                except Exception:
                    pass

            self._statuses[platform] = SessionStatus.EXPIRED
            logger.warning(f"Session EXPIRED for platform: '{platform}'")
            return SessionStatus.EXPIRED

        except Exception as e:
            logger.error(f"Error during session health check for '{platform}': {e}")
            self._statuses[platform] = SessionStatus.DEGRADED
            return SessionStatus.DEGRADED

    async def open_headed_login(self, browser_pool: Any, platform: str, timeout_sec: int = 120) -> bool:
        """Launches a visible headed browser context allowing user to manually log in.

        Args:
            browser_pool: BrowserPool instance.
            platform: Platform identifier to authenticate.
            timeout_sec: Maximum duration to wait for user login.

        Returns:
            bool: True if user successfully logged in within timeout.
        """
        logger.info(f"Launching headed browser for manual user authentication to '{platform}'...")
        url_map = {
            "gemini_web": settings.GEMINI_WEB_URL,
            "linkedin": settings.LINKEDIN_WEB_URL,
            "x_twitter": settings.X_TWITTER_WEB_URL,
        }
        target_url = url_map.get(platform, settings.GEMINI_WEB_URL)
        page = await browser_pool.new_page(headless=False)

        try:
            await page.goto(target_url)
            logger.info(f"Please complete login in the opened browser window. Polling up to {timeout_sec}s...")

            for _ in range(timeout_sec):
                status = await self.verify_session(page, platform)
                if status == SessionStatus.HEALTHY:
                    logger.info(f"Manual authentication verified! Session saved for '{platform}'.")
                    return True
                await page.wait_for_timeout(1000)

            logger.warning(f"Manual login timed out for '{platform}' after {timeout_sec}s.")
            return False
        finally:
            await page.close()

session_health_mgr = SessionHealthManager()
