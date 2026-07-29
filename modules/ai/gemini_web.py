import asyncio
import logging

from config.settings import settings
from modules.ai.base import BaseAIProvider
from modules.browser.pool import browser_pool
from modules.browser.selector_manager import selector_manager
from modules.browser.stealth import stealth

logger = logging.getLogger("AIContentOS.GeminiWeb")

class GeminiWebProvider(BaseAIProvider):
    @property
    def name(self) -> str:
        return "gemini_web"

    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        page = await browser_pool.new_page()
        try:
            logger.info(f"Navigating to Gemini Web: {settings.GEMINI_WEB_URL}")
            await page.goto(settings.GEMINI_WEB_URL, timeout=settings.NAVIGATION_TIMEOUT)
            await stealth.wait_human_pause(2.0, 4.0)

            # Combine system instruction and user prompt if provided
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

            # Resolve textarea using fallback selectors
            textarea = await selector_manager.find_element(page, "gemini_web", "prompt_textarea")
            await textarea.click()
            await stealth.type_like_human(textarea, full_prompt)
            await stealth.wait_human_pause(1.0, 2.0)

            # Click Submit button
            submit_btn = await selector_manager.find_element(page, "gemini_web", "submit_button")
            await submit_btn.click()
            logger.info("Prompt submitted to Gemini Web. Waiting for output generation...")

            # Wait for generation to complete (polling response panel text stability)
            response_container = await selector_manager.find_element(page, "gemini_web", "response_container")

            # Poll until response stabilizes
            last_text = ""
            stable_count = 0
            for _ in range(60):  # max 60 seconds
                await asyncio.sleep(1.0)
                current_text = await response_container.inner_text()
                if current_text and current_text == last_text:
                    stable_count += 1
                    if stable_count >= 3:  # Stable for 3 consecutive seconds
                        logger.info("Gemini response generation completed & stabilized.")
                        return current_text
                else:
                    last_text = current_text
                    stable_count = 0

            return last_text
        except Exception as e:
            logger.error(f"GeminiWebProvider error: {e}")
            await browser_pool.capture_failure_artifact(page, "gemini_gen")
            raise e
        finally:
            await page.close()

    async def check_health(self) -> bool:
        page = await browser_pool.new_page()
        try:
            await page.goto(settings.GEMINI_WEB_URL, timeout=15000)
            textarea = await selector_manager.find_element(page, "gemini_web", "prompt_textarea")
            return textarea is not None
        except Exception:
            return False
        finally:
            await page.close()
