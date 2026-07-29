"""Selector registry module for AI Content OS.

Loads external DOM selectors configuration (selectors.json), provides ordered fallback
selector queries, and validates page element presence using Loguru logging.
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from config.settings import settings


class SelectorRegistry:
    """Registry managing externalized DOM selectors with multi-selector fallback logic."""

    def __init__(self, selectors_file: Path = settings.BASE_DIR / "config" / "selectors.json"):
        self.selectors_file: Path = selectors_file
        self._data: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Loads and parses the JSON selector configuration file."""
        if not self.selectors_file.exists():
            logger.warning(f"Selectors registry file missing at '{self.selectors_file}'")
            self._data = {}
            return

        try:
            with open(self.selectors_file, encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(
                f"Loaded DOM selector registry from '{self.selectors_file}' "
                f"({len(self._data)} services defined)."
            )
        except Exception as e:
            logger.error(f"Failed to parse selectors JSON from '{self.selectors_file}': {e}")
            self._data = {}

    def get_selectors(self, service: str, element_name: str) -> list[str]:
        """Returns ordered list of fallback CSS/XPath selectors for a given service and element.

        Args:
            service: Target platform/service identifier (e.g., 'gemini_web', 'linkedin_web').
            element_name: Target UI element name (e.g., 'prompt_textarea', 'submit_button').

        Returns:
            List[str]: Ordered list of fallback selector strings.
        """
        service_data = self._data.get(service, {})
        selectors = service_data.get(element_name, [])
        if isinstance(selectors, str):
            return [selectors]
        return list(selectors)

    def validate_registry(self) -> bool:
        """Validates that selector registry is non-empty and well-formed.

        Returns:
            bool: True if registry contains valid configuration dictionary, False otherwise.
        """
        if not self._data:
            logger.warning("Selector registry validation failed: Registry is empty.")
            return False
        for service, elements in self._data.items():
            if not isinstance(elements, dict):
                logger.error(f"Invalid service entry in selector registry for '{service}'")
                return False
        logger.debug("Selector registry validation passed.")
        return True

    async def find_element(self, page: Any, service: str, element_name: str) -> Any:
        """Sequential fallback query resolver trying selectors until element is matched.

        Args:
            page: Playwright Page instance.
            service: Target platform identifier.
            element_name: Target UI element name.

        Returns:
            Locator: Matched Playwright Locator element.
        """
        selectors = self.get_selectors(service, element_name)
        if not selectors:
            raise KeyError(f"No selectors registered for [{service}.{element_name}]")

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    logger.debug(f"Resolved [{service}.{element_name}] via selector: '{selector}'")
                    return locator
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed for [{service}.{element_name}]: {e}")

        raise RuntimeError(f"Failed to find element [{service}.{element_name}] using selectors: {selectors}")

selector_registry = SelectorRegistry()
