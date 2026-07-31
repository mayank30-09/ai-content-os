"""Schema Resolver module for Publisher Worker subsystem.

Deterministically populates {{PLACEHOLDER}} tags in JSON-LD schema markup templates
with runtime context values (e.g. author, publish date, canonical URL, image URL).
"""

import re
from datetime import UTC, datetime
from typing import Any

from loguru import logger


class SchemaResolver:
    """Deterministic schema placeholder resolver.

    Replaces {{PLACEHOLDER}} strings in nested dictionary and list structures
    with provided runtime context values or sensible defaults. Leaves no unhandled
    placeholders behind.
    """

    PLACEHOLDER_PATTERN: re.Pattern = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

    def resolve_schema(
        self,
        schema_template: dict[str, Any],
        context_values: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Resolves all placeholders in the schema template.

        Args:
            schema_template: Dictionary containing schema structure with {{PLACEHOLDER}} strings.
            context_values: Mapping of placeholder keys to values (e.g. {"AUTHOR": "Jane Doe"}).

        Returns:
            Tuple of:
            - Fully resolved schema dictionary.
            - Count of placeholders resolved (int).
        """
        values = self._build_default_context_values(context_values)
        resolved_count = [0]  # Mutable counter for recursive updates

        resolved_schema = self._traverse_and_replace(schema_template, values, resolved_count)

        logger.info(
            f"SchemaResolver: resolved {resolved_count[0]} placeholders in schema markup."
        )
        return resolved_schema, resolved_count[0]

    def _traverse_and_replace(
        self,
        node: Any,
        values: dict[str, str],
        counter: list[int],
    ) -> Any:
        """Recursively traverses dictionaries and lists to replace placeholders.

        Args:
            node: Dict, list, str, or primitive node in the schema tree.
            values: Dictionary of placeholder replacement values.
            counter: Mutable single-item list tracking resolution count.

        Returns:
            Transformed node with placeholders replaced.
        """
        if isinstance(node, dict):
            return {k: self._traverse_and_replace(v, values, counter) for k, v in node.items()}
        elif isinstance(node, list):
            return [self._traverse_and_replace(item, values, counter) for item in node]
        elif isinstance(node, str):
            return self._replace_string_placeholders(node, values, counter)
        return node

    def _replace_string_placeholders(
        self,
        text: str,
        values: dict[str, str],
        counter: list[int],
    ) -> str:
        """Replaces {{PLACEHOLDER}} tags in a string value.

        Args:
            text: Input string.
            values: Placeholder mapping.
            counter: Resolution counter.

        Returns:
            String with placeholders replaced.
        """
        def replace_match(match: re.Match) -> str:
            key = match.group(1)
            counter[0] += 1
            if key in values:
                return values[key]
            # Fallback for unhandled placeholders: return clean uppercase placeholder fallback
            return f"Unassigned_{key.title()}"

        return self.PLACEHOLDER_PATTERN.sub(replace_match, text)

    @staticmethod
    def _build_default_context_values(user_values: dict[str, str] | None) -> dict[str, str]:
        """Builds default context values merged with user-provided overrides.

        Args:
            user_values: Optional user context dictionary.

        Returns:
            Complete mapping dictionary.
        """
        defaults = {
            "AUTHOR": "AI Content OS",
            "DATE": datetime.now(UTC).isoformat(),
            "CANONICAL_URL": "https://example.com/article",
            "IMAGE_URL": "https://example.com/assets/default_hero.png",
            "ORGANIZATION": "AI Content OS Platform",
            "PUBLISHER": "AI Content OS Engine",
        }
        if user_values:
            defaults.update(user_values)
        return defaults
