import logging
from enum import Enum

from config.settings import settings
from modules.browser.pool import browser_pool
from modules.browser.selector_manager import selector_manager

logger = logging.getLogger("AIContentOS.SessionHealth")

class SessionStatus(Enum):
    HEALTHY = "HEALTHY"
    EXPIRED = "EXPIRED"
    DEGRADED = "DEGRADED"

class SessionHealthManager:
    def __init__(self):
        self.platform_status: dict[str, SessionStatus] = {
            "gemini_web": SessionStatus.EXPIRED,
            "linkedin": SessionStatus.EXPIRED,
            "x_twitter": SessionStatus.EXPIRED
        }

    async def verify_session(self, platform: str) -> SessionStatus:
        """Verifies session health for a given platform."""
        logger.info(f"Verifying session health for platform: {platform}")
        page = await browser_pool.new_page()
        try:
            if platform == "gemini_web":
                await page.goto(settings.GEMINI_WEB_URL, timeout=20000)
                try:
                    elem = await selector_manager.find_element(page, "gemini_web", "prompt_textarea")
                    if elem:
                        self.platform_status[platform] = SessionStatus.HEALTHY
                        return SessionStatus.HEALTHY
                except Exception:
                    pass

            elif platform == "linkedin":
                await page.goto(settings.LINKEDIN_WEB_URL, timeout=20000)
                try:
                    elem = await selector_manager.find_element(page, "linkedin_web", "start_post_button")
                    if elem:
                        self.platform_status[platform] = SessionStatus.HEALTHY
                        return SessionStatus.HEALTHY
                except Exception:
                    pass

            self.platform_status[platform] = SessionStatus.EXPIRED
            logger.warning(f"Session EXPIRED for platform: {platform}")
            return SessionStatus.EXPIRED
        except Exception as e:
            logger.error(f"Error checking session for {platform}: {e}")
            self.platform_status[platform] = SessionStatus.DEGRADED
            return SessionStatus.DEGRADED
        finally:
            await page.close()

    async def open_headed_login(self, platform: str, timeout_sec: int = 120):
        """Launches a headed browser instance allowing the user to manually log in and save session state."""
        logger.info(f"Opening headed browser for manual user login to {platform}...")
        url_map = {
            "gemini_web": settings.GEMINI_WEB_URL,
            "linkedin": settings.LINKEDIN_WEB_URL,
            "x_twitter": settings.X_TWITTER_WEB_URL
        }
        target_url = url_map.get(platform, settings.GEMINI_WEB_URL)

        # Launch headed browser context specifically for authentication
        playwright = await browser_pool.get_context()
        page = await playwright.new_page()
        try:
            await page.goto(target_url)
            logger.info(f"Please log into {platform} in the opened browser window. Waiting up to {timeout_sec}s...")
            # Wait for user manual login
            for _ in range(timeout_sec):
                status = await self.verify_session(platform)
                if status == SessionStatus.HEALTHY:
                    logger.info(f"Manual login verified! Session state saved for {platform}.")
                    return True
                await page.wait_for_timeout(1000)
            return False
        finally:
            await page.close()

session_health_mgr = SessionHealthManager()
