"""Stealth layer module for AI Content OS.

Provides human interaction simulation routines including micro-delayed typing,
natural mouse bezier trajectories, page scrolling, and randomized pauses.
"""

import asyncio
import random
from typing import Any

from loguru import logger

from config.settings import settings


class StealthLayer:
    """Simulates realistic human user behavior during browser automation."""

    @staticmethod
    async def type_like_human(element: Any, text: str) -> None:
        """Types text into an input element with randomized keystroke micro-delays.

        Args:
            element: Playwright Locator or ElementHandle input element.
            text: Text string to type.
        """
        for char in text:
            await element.type(char)
            delay = random.randint(
                settings.HUMAN_TYPING_MIN_DELAY_MS,
                settings.HUMAN_TYPING_MAX_DELAY_MS
            ) / 1000.0
            await asyncio.sleep(delay)

    @staticmethod
    async def random_scroll(page: Any, min_px: int = 300, max_px: int = 700) -> None:
        """Performs a natural vertical scroll on the page.

        Args:
            page: Playwright Page instance.
            min_px: Minimum scroll distance in pixels.
            max_px: Maximum scroll distance in pixels.
        """
        scroll_amount = random.randint(min_px, max_px)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.5, 1.2))

    @staticmethod
    async def random_mouse_movement(page: Any) -> None:
        """Simulates natural random mouse movements on the viewport.

        Args:
            page: Playwright Page instance.
        """
        viewport = page.viewport_size or {"width": 1280, "height": 800}
        target_x = random.randint(100, viewport["width"] - 100)
        target_y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(target_x, target_y, steps=random.randint(5, 15))
        logger.debug(f"Simulated mouse movement to ({target_x}, {target_y})")

    @staticmethod
    async def wait_human_pause(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
        """Pauses execution for a randomized human thinking/reading duration.

        Args:
            min_sec: Minimum pause time in seconds.
            max_sec: Maximum pause time in seconds.
        """
        pause_duration = random.uniform(min_sec, max_sec)
        await asyncio.sleep(pause_duration)

stealth_layer = StealthLayer()
