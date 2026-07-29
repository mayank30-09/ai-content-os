import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from config.settings import settings

logger = logging.getLogger("AIContentOS.BrowserPool")

class PlaywrightBrowserPool:
    def __init__(self):
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None

    async def get_context(self, user_data_dir: Path = settings.GEMINI_PROFILE_DIR) -> BrowserContext:
        """Gets or launches a persistent browser context with stealth parameters."""
        if self._context is None:
            self._playwright = await async_playwright().start()
            user_data_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Launching Playwright persistent context at: {user_data_dir}")
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=settings.HEADLESS,
                slow_mo=settings.BROWSER_SLOW_MO,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
        return self._context

    async def new_page(self, user_data_dir: Path = settings.GEMINI_PROFILE_DIR) -> Page:
        context = await self.get_context(user_data_dir)
        page = await context.new_page()
        # Set extra HTTP headers to reduce bot flags
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9"
        })
        return page

    async def capture_failure_artifact(self, page: Page, name_prefix: str) -> Path:
        """Saves screenshot and HTML dump on failure for observability."""
        settings.FAILURE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{name_prefix}_failure.png"
        screenshot_path = settings.FAILURE_LOGS_DIR / filename
        await page.screenshot(path=str(screenshot_path), full_page=True)

        html_path = settings.FAILURE_LOGS_DIR / f"{name_prefix}_failure.html"
        html_content = await page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.warning(f"Failure artifact captured: {screenshot_path}")
        return screenshot_path

    async def close(self):
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright browser pool closed")

browser_pool = PlaywrightBrowserPool()
