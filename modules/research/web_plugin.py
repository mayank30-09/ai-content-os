import logging
from typing import Any

from modules.browser.pool import browser_pool
from modules.research.base import BaseResearchPlugin

logger = logging.getLogger("AIContentOS.WebResearchPlugin")

class WebResearchPlugin(BaseResearchPlugin):
    @property
    def source_name(self) -> str:
        return "web"

    async def can_handle(self, target: str) -> bool:
        return target.startswith("http://") or target.startswith("https://")

    async def extract_content(self, target: str) -> dict[str, Any]:
        logger.info(f"Extracting web research content from: {target}")
        page = await browser_pool.new_page()
        try:
            await page.goto(target, timeout=30000)
            title = await page.title()

            # Extract main text paragraphs
            paragraphs = await page.locator("p").all_inner_texts()
            clean_body = " ".join([p.strip() for p in paragraphs if len(p.strip()) > 30])

            # Truncate to first 3000 chars to avoid token blowout
            truncated_body = clean_body[:3000]

            return {
                "source": "web",
                "url": target,
                "title": title,
                "content_body": truncated_body
            }
        except Exception as e:
            logger.error(f"WebResearchPlugin error on {target}: {e}")
            return {
                "source": "web",
                "url": target,
                "title": "Failed extraction",
                "content_body": f"Extraction failed: {str(e)}"
            }
        finally:
            await page.close()
