"""Web page research scraper plugin module for AI Content OS.

Extracts clean text content and page metadata from target URLs using Playwright.
"""

from typing import Any

from loguru import logger

from modules.browser.pool import browser_pool
from modules.research.base import BaseResearchPlugin


class WebResearchPlugin(BaseResearchPlugin):
    """Research plugin for scraping web articles and blogs."""

    @property
    def source_name(self) -> str:
        """Returns plugin source identifier."""
        return "web"

    async def can_handle(self, target: str) -> bool:
        """Checks if target string is an HTTP/HTTPS URL."""
        return target.startswith("http://") or target.startswith("https://")

    async def extract_content(self, target: str) -> dict[str, Any]:
        """Navigates to URL and extracts clean body text content."""
        logger.info(f"Extracting web research content from: '{target}'")
        page = await browser_pool.new_page()
        try:
            await page.goto(target, timeout=30000)
            title = await page.title()

            paragraphs = await page.locator("p").all_inner_texts()
            clean_body = " ".join([p.strip() for p in paragraphs if len(p.strip()) > 30])
            truncated_body = clean_body[:3000]

            return {
                "source": "web",
                "url": target,
                "title": title,
                "content_body": truncated_body,
            }
        except Exception as e:
            logger.error(f"WebResearchPlugin error on '{target}': {e}")
            return {
                "source": "web",
                "url": target,
                "title": "Failed extraction",
                "content_body": f"Extraction failed: {str(e)}",
            }
        finally:
            await page.close()
