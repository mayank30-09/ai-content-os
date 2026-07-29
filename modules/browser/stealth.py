import asyncio
import logging
import random

from config.settings import settings

logger = logging.getLogger("AIContentOS.Stealth")

class StealthDriver:
    @staticmethod
    async def type_like_human(element, text: str):
        """Types text with randomized micro-delays between keystrokes to mimic human behavior."""
        for char in text:
            await element.type(char)
            delay = random.randint(
                settings.HUMAN_TYPING_MIN_DELAY_MS,
                settings.HUMAN_TYPING_MAX_DELAY_MS
            ) / 1000.0
            await asyncio.sleep(delay)

    @staticmethod
    async def random_scroll(page):
        """Performs natural mouse wheel scrolling on page."""
        scroll_amount = random.randint(300, 700)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.5, 1.2))

    @staticmethod
    async def wait_human_pause(min_sec: float = 1.0, max_sec: float = 3.0):
        """Simulates natural human reading/thinking pauses."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

stealth = StealthDriver()
