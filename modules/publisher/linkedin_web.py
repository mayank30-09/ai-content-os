"""LinkedIn Web Publisher module for AI Content OS.

Automates posting to LinkedIn web feed using Playwright, protected by the Hardened
Human Approval Gate.
"""

from typing import Any

from loguru import logger

from config.settings import settings
from modules.browser.pool import browser_pool
from modules.browser.selector_manager import selector_registry
from modules.browser.stealth import stealth_layer
from modules.memory.repositories import content_repo, logger_repo
from modules.publisher.base import BasePublisher


class LinkedInWebPublisher(BasePublisher):
    """Web publisher driving LinkedIn web interface for content post creation."""

    @property
    def platform_name(self) -> str:
        """Returns platform identifier name."""
        return "linkedin"

    async def publish(self, content_item: dict[str, Any]) -> bool:
        """Publishes approved content item to LinkedIn web feed."""
        content_id = content_item["id"]

        if not content_item.get("is_human_approved"):
            logger.critical(f"PUBLISHING REJECTED: Content ID '{content_id}' is NOT human approved!")
            logger_repo.log(content_id, "PUBLISH", "ERROR", "Attempted to publish without human approval!")
            raise ValueError("Cannot publish content that has not passed Human Approval Gate.")

        logger.info(f"Initiating automated LinkedIn post for content_id: '{content_id}'")
        logger_repo.log(content_id, "PUBLISH", "INFO", "Navigating to LinkedIn Web Feed")

        page = await browser_pool.new_page()
        try:
            await page.goto(settings.LINKEDIN_WEB_URL, timeout=settings.NAVIGATION_TIMEOUT)
            await stealth_layer.wait_human_pause(2.0, 4.0)

            start_post_btn = await selector_registry.find_element(page, "linkedin_web", "start_post_button")
            await start_post_btn.click()
            await stealth_layer.wait_human_pause(1.0, 2.0)

            post_text = content_item.get("caption_text") or content_item.get("ai_raw_output", "")

            textarea = await selector_registry.find_element(page, "linkedin_web", "post_modal_textarea")
            await textarea.click()
            await stealth_layer.type_like_human(textarea, post_text)
            await stealth_layer.wait_human_pause(1.5, 3.0)

            publish_btn = await selector_registry.find_element(page, "linkedin_web", "publish_button")
            await publish_btn.click()
            await stealth_layer.wait_human_pause(3.0, 5.0)

            content_repo.mark_published(content_id)
            logger_repo.log(content_id, "PUBLISH", "SUCCESS", "Content successfully posted to LinkedIn!")
            return True
        except Exception as e:
            logger.error(f"LinkedIn publishing failed for content_id '{content_id}': {e}")
            await browser_pool.capture_failure_artifact(page, f"linkedin_pub_{content_id}")
            logger_repo.log(content_id, "PUBLISH", "ERROR", f"LinkedIn publishing error: {str(e)}")
            raise e
        finally:
            await page.close()
