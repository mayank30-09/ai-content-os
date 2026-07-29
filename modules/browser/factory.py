"""Browser factory module for AI Content OS.

Creates Playwright browser instances and persistent browser contexts with configurable
headless/headed modes, stealth flags, viewport dimensions, and user agents.
"""

from pathlib import Path

from loguru import logger
from playwright.async_api import BrowserContext, Playwright

from config.settings import settings


class BrowserFactory:
    """Factory responsible for instantiating Playwright browser contexts."""

    DEFAULT_ARGS: list[str] = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-position=0,0",
        "--ignore-certificate-errors",
    ]

    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    @classmethod
    async def create_persistent_context(
        cls,
        playwright: Playwright,
        user_data_dir: Path,
        headless: bool | None = None,
        slow_mo: int | None = None,
        extra_args: list[str] | None = None,
    ) -> BrowserContext:
        """Launches a persistent Playwright Chromium browser context.

        Args:
            playwright: Active Playwright engine instance.
            user_data_dir: Path to the user profile directory for session persistence.
            headless: Override for headless mode execution.
            slow_mo: Delay in milliseconds between Playwright actions.
            extra_args: Additional command line flags for Chromium.

        Returns:
            BrowserContext: Configured persistent browser context.
        """
        is_headless = settings.HEADLESS if headless is None else headless
        action_delay = settings.BROWSER_SLOW_MO if slow_mo is None else slow_mo
        args = cls.DEFAULT_ARGS + (extra_args or [])

        user_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Creating Playwright persistent context at '{user_data_dir}' "
            f"[Headless: {is_headless}, SlowMo: {action_delay}ms]"
        )

        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=is_headless,
                slow_mo=action_delay,
                viewport={"width": 1280, "height": 800},
                user_agent=cls.DEFAULT_USER_AGENT,
                args=args,
                ignore_https_errors=True,
            )
            logger.info("Successfully created persistent browser context.")
            return context
        except Exception as e:
            logger.error(f"Failed to create persistent browser context at '{user_data_dir}': {e}")
            raise e

browser_factory = BrowserFactory()
