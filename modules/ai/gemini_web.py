"""Production-grade Gemini Web AI Provider adapter for AI Content OS.

Implements exponential backoff smart retries, automatic popup dismissal, session health
verification, loading state detection, output validation, and failure screenshot dumps.
"""

import asyncio

from loguru import logger

from config.settings import settings
from modules.ai.base import BaseAIProvider
from modules.browser.pool import browser_pool
from modules.browser.selector_manager import selector_registry
from modules.browser.session_health import session_health_mgr
from modules.browser.stealth import stealth_layer


class GeminiWebError(Exception):
    """Base exception for Gemini Web automation errors."""
    pass

class SessionExpiredException(GeminiWebError):
    """Raised when Gemini user session has expired or login is required."""
    pass

class ResponseValidationException(GeminiWebError):
    """Raised when Gemini response fails validation checks (empty, error page, too short)."""
    pass

class GenerationTimeoutException(GeminiWebError):
    """Raised when Gemini generation exceeds the configured timeout budget."""
    pass

class GeminiWebProvider(BaseAIProvider):
    """Production-hardened AI Provider driving Gemini Pro web subscription interface."""

    ERROR_SUBSTRINGS = [
        "something went wrong",
        "an error occurred",
        "500 internal error",
        "404 not found",
        "service unavailable",
        "please try again later",
    ]

    @property
    def name(self) -> str:
        """Returns provider identifier string."""
        return "gemini_web"

    async def dismiss_popups(self, page: str) -> int:
        """Finds and clicks visible popups, onboarding dialogs, or cookie banners."""
        dismissed_count = 0
        popup_selectors = selector_registry.get_selectors("gemini_web", "popup_dismiss_buttons")
        for selector in popup_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    logger.info(f"Dismissing detected popup/dialog using selector: '{selector}'")
                    await button.click()
                    dismissed_count += 1
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"Popup check for '{selector}' passed: {e}")
        return dismissed_count

    def validate_response(self, text: str) -> bool:
        """Validates extracted AI text output against non-empty, length, and error rules.

        Args:
            text: Extracted raw response text.

        Returns:
            bool: True if valid. Raises ResponseValidationException otherwise.
        """
        if not text or not text.strip():
            raise ResponseValidationException("Gemini response is completely empty.")

        cleaned = text.strip()
        if len(cleaned) < settings.GEMINI_MIN_RESPONSE_LENGTH:
            raise ResponseValidationException(
                f"Gemini response length ({len(cleaned)} chars) below minimum threshold ({settings.GEMINI_MIN_RESPONSE_LENGTH})."
            )

        lower_text = cleaned.lower()
        for err_sub in self.ERROR_SUBSTRINGS:
            if err_sub in lower_text:
                raise ResponseValidationException(f"Gemini response contains error message indicator: '{err_sub}'")

        return True

    async def _wait_for_generation_complete(self, page: str, timeout_sec: int) -> str:
        """Polls response container until generation loading indicators clear and text stabilizes."""
        response_container = await selector_registry.find_element(page, "gemini_web", "response_container")

        last_text = ""
        stable_seconds = 0

        for _ in range(timeout_sec):
            await asyncio.sleep(1.0)

            # Check if stop button or loading indicator is active
            loading_selectors = selector_registry.get_selectors("gemini_web", "loading_indicators")
            is_loading = False
            for sel in loading_selectors:
                try:
                    indicator = page.locator(sel).first
                    if await indicator.count() > 0 and await indicator.is_visible():
                        is_loading = True
                        break
                except Exception:
                    pass

            current_text = await response_container.inner_text()
            if not is_loading and current_text and current_text == last_text:
                stable_seconds += 1
                if stable_seconds >= 3:
                    logger.info("Generation completed and output text stabilized.")
                    return current_text
            else:
                last_text = current_text
                stable_seconds = 0

        raise GenerationTimeoutException(f"Generation did not complete within {timeout_sec} seconds timeout.")

    async def _attempt_single_generation(self, page: str, full_prompt: str) -> str:
        """Executes single prompt delivery flow on page."""
        logger.info(f"Opening Gemini Web interface: {settings.GEMINI_WEB_URL}")
        await page.goto(settings.GEMINI_WEB_URL, timeout=settings.NAVIGATION_TIMEOUT)
        await stealth_layer.wait_human_pause(1.5, 3.0)

        # Handle any initial popups/announcements
        await self.dismiss_popups(page)

        # Verify session health
        try:
            textarea = await selector_registry.find_element(page, "gemini_web", "prompt_textarea")
        except Exception as e:
            logger.error(f"Failed to find prompt textarea. Session may be expired: {e}")
            await session_health_mgr.verify_session(page, "gemini_web")
            raise SessionExpiredException("Gemini user session expired or login required.") from e

        # Type prompt with human simulation
        logger.info("Typing prompt into Gemini input area...")
        await textarea.click()
        await stealth_layer.type_like_human(textarea, full_prompt)
        await stealth_layer.wait_human_pause(1.0, 2.0)

        # Submit prompt
        logger.info("Submitting prompt to Gemini...")
        submit_btn = await selector_registry.find_element(page, "gemini_web", "submit_button")
        await submit_btn.click()

        # Wait for generation to finish
        logger.info(f"Waiting for Gemini output generation (Timeout: {settings.GEMINI_GENERATION_TIMEOUT}s)...")
        raw_response = await self._wait_for_generation_complete(page, settings.GEMINI_GENERATION_TIMEOUT)

        # Validate response
        self.validate_response(raw_response)
        return raw_response

    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        """Sends prompt to Gemini Web with exponential backoff retries and failure dumps."""
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        max_retries = settings.GEMINI_MAX_RETRIES

        for attempt in range(1, max_retries + 1):
            page = await browser_pool.new_page()
            try:
                logger.info(f"Gemini Web Generation Attempt {attempt}/{max_retries}")
                result = await self._attempt_single_generation(page, full_prompt)
                if attempt > 1:
                    logger.info(f"Successfully recovered on attempt {attempt}/{max_retries}!")
                logger.info("Completed Gemini response extraction successfully.")
                return result
            except SessionExpiredException as e:
                logger.critical(f"Unrecoverable session error on attempt {attempt}: {e}")
                await browser_pool.capture_failure_artifact(page, f"gemini_session_expired_attempt_{attempt}")
                raise e
            except (GenerationTimeoutException, ResponseValidationException, Exception) as e:
                logger.warning(f"Generation attempt {attempt}/{max_retries} failed: {e}")
                await browser_pool.capture_failure_artifact(page, f"gemini_failure_attempt_{attempt}")

                if attempt == max_retries:
                    logger.error(f"All {max_retries} retries exhausted for Gemini generation.")
                    raise e

                backoff_delay = settings.GEMINI_RETRY_BACKOFF_FACTOR ** attempt
                logger.info(f"Retrying in {backoff_delay:.1f}s (Exponential Backoff)...")
                await asyncio.sleep(backoff_delay)
            finally:
                await page.close()

        raise GeminiWebError("Unexpected retry loop termination.")

    async def check_health(self) -> bool:
        """Checks whether Gemini web interface is accessible and prompt input is available."""
        page = await browser_pool.new_page()
        try:
            await page.goto(settings.GEMINI_WEB_URL, timeout=15000)
            await self.dismiss_popups(page)
            textarea = await selector_registry.find_element(page, "gemini_web", "prompt_textarea")
            return textarea is not None
        except Exception:
            return False
        finally:
            await page.close()
