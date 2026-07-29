import json
import logging
from pathlib import Path

from config.settings import settings

logger = logging.getLogger("AIContentOS.SelectorManager")

class SelectorManager:
    def __init__(self, selectors_file: Path = settings.BASE_DIR / "config" / "selectors.json"):
        self.selectors_file = selectors_file
        self.data = self._load()

    def _load(self) -> dict:
        if not self.selectors_file.exists():
            logger.warning(f"Selectors file not found: {self.selectors_file}")
            return {}
        with open(self.selectors_file, encoding="utf-8") as f:
            return json.load(f)

    def get_selectors(self, service: str, element_name: str) -> list[str]:
        """Returns ordered list of fallback selectors for a given service and element."""
        service_data = self.data.get(service, {})
        selectors = service_data.get(element_name, [])
        if isinstance(selectors, str):
            return [selectors]
        return selectors

    async def find_element(self, page, service: str, element_name: str):
        """Tries primary and fallback selectors sequentially until one matches on page."""
        selectors = self.get_selectors(service, element_name)
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    logger.debug(f"Resolved [{service}.{element_name}] via selector: '{selector}'")
                    return element
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed for [{service}.{element_name}]: {e}")

        raise RuntimeError(f"Failed to find element [{service}.{element_name}] using selectors: {selectors}")

selector_manager = SelectorManager()
