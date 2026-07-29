"""Browser pool module for AI Content OS.

Manages active Playwright instance, persistent context reuse, new tab creation,
and failure artifact (screenshot and DOM HTML) logging.
"""

from pathlib import Path

from loguru import logger
from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from config.settings import settings
from modules.browser.daemon import browser_daemon
from modules.browser.factory import browser_factory


class BrowserPool:
    """Pool managing Playwright lifecycle, persistent context reuse, and page creation."""

    def __init__(self):
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._active_user_dir: Path | None = None

    async def get_context(
        self,
        user_data_dir: Path | None = None,
        headless: bool | None = None,
    ) -> BrowserContext:
        """Gets existing persistent context or initializes a new context.

        Args:
            user_data_dir: Profile directory path. Defaults to settings.GEMINI_PROFILE_DIR.
            headless: Override for headless execution.

        Returns:
            BrowserContext: Active persistent browser context.
        """
        target_dir = user_data_dir or settings.GEMINI_PROFILE_DIR

        # If context exists and directory matches, reuse existing context
        if self._context and self._active_user_dir == target_dir:
            return self._context

        # Pre-startup cleanup daemon: clean stale locks & orphan processes
        browser_daemon.prepare_startup(target_dir)

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self._context = await browser_factory.create_persistent_context(
            playwright=self._playwright,
            user_data_dir=target_dir,
            headless=headless,
        )
        self._active_user_dir = target_dir
        return self._context

    async def new_page(
        self,
        user_data_dir: Path | None = None,
        headless: bool | None = None,
    ) -> Page:
        """Creates and returns a new Page tab inside the context.

        Args:
            user_data_dir: Target profile directory path.
            headless: Override for headless execution.

        Returns:
            Page: Newly created Playwright Page instance.
        """
        context = await self.get_context(user_data_dir=user_data_dir, headless=headless)
        page = await context.new_page()
        await page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
        logger.debug(f"Created new page in browser context [Profile: '{self._active_user_dir}']")
        return page

    async def capture_failure_artifact(self, page: Page, name_prefix: str) -> Path:
        """Captures full-page screenshot and HTML DOM dump on execution error.

        Args:
            page: Playwright Page instance.
            name_prefix: Prefix for artifact file names.

        Returns:
            Path: Path to saved screenshot artifact.
        """
        settings.FAILURE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        screenshot_path = settings.FAILURE_LOGS_DIR / f"{name_prefix}_failure.png"
        html_path = settings.FAILURE_LOGS_DIR / f"{name_prefix}_failure.html"

        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            html_content = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.warning(f"Failure artifact saved: Screenshot='{screenshot_path}', DOM Dump='{html_path}'")
        except Exception as e:
            logger.error(f"Failed to capture failure artifact: {e}")

        return screenshot_path

    async def close(self) -> None:
        """Gracefully closes context and stops Playwright engine."""
        if self._context:
            try:
                await self._context.close()
                logger.info("Closed persistent browser context.")
            except Exception as e:
                logger.warning(f"Error closing browser context: {e}")
            self._context = None
            self._active_user_dir = None

        if self._playwright:
            try:
                await self._playwright.stop()
                logger.info("Stopped Playwright engine.")
            except Exception as e:
                logger.warning(f"Error stopping Playwright engine: {e}")
            self._playwright = None

browser_pool = BrowserPool()
