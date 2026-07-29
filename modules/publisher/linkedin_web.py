import logging
from typing import Any

from config.settings import settings
from modules.browser.pool import browser_pool
from modules.browser.selector_manager import selector_manager
from modules.browser.stealth import stealth
from modules.memory.repositories import content_repo, logger_repo
from modules.publisher.base import BasePublisher

logger = logging.getLogger("AIContentOS.LinkedInPublisher")

class LinkedInWebPublisher(BasePublisher):
    @property
    def platform_name(self) -> str:
        return "linkedin"

    async def publish(self, content_item: dict[str, Any]) -> bool:
        content_id = content_item["id"]

        # HARDENED INVARIANT: Human Approval Gate Verification
        if not content_item.get("is_human_approved"):
            logger.critical(f"PUBLISHING REJECTED: Content ID {content_id} is NOT human approved!")
            logger_repo.log(content_id, "PUBLISH", "ERROR", "Attempted to publish without human approval!")
            raise ValueError("Cannot publish content that has not passed Human Approval Gate.")

        logger.info(f"Initiating automated LinkedIn post for content_id: {content_id}")
        logger_repo.log(content_id, "PUBLISH", "INFO", "Navigating to LinkedIn Web Feed")

        page = await browser_pool.new_page()
        try:
            await page.goto(settings.LINKEDIN_WEB_URL, timeout=settings.NAVIGATION_TIMEOUT)
            await stealth.wait_human_pause(2.0, 4.0)

            # Click "Start a post" button
            start_post_btn = await selector_manager.find_element(page, "linkedin_web", "start_post_button")
            await start_post_btn.click()
            await stealth.wait_human_pause(1.0, 2.0)

            # Get caption text
            post_text = content_item.get("caption_text") or content_item.get("ai_raw_output", "")

            # Fill post modal text area
            textarea = await selector_manager.find_element(page, "linkedin_web", "post_modal_textarea")
            await textarea.click()
            await stealth.type_like_human(textarea, post_text)
            await stealth.wait_human_pause(1.5, 3.0)

            # Click Publish button
            publish_btn = await selector_manager.find_element(page, "linkedin_web", "publish_button")
            await publish_btn.click()
            await stealth.wait_human_pause(3.0, 5.0)

            # Mark as published in repository
            content_repo.mark_published(content_id)
            logger_repo.log(content_id, "PUBLISH", "SUCCESS", "Content successfully posted to LinkedIn!")
            return True
        except Exception as e:
            logger.error(f"LinkedIn publishing failed for content_id {content_id}: {e}")
            await browser_pool.capture_failure_artifact(page, f"linkedin_pub_{content_id}")
            logger_repo.log(content_id, "PUBLISH", "ERROR", f"LinkedIn publishing error: {str(e)}")
            raise e
        finally:
            await page.close()
