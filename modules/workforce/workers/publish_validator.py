"""Publish Validator for Publisher Worker subsystem.

Performs pre-publish readiness audits on constructed platform payloads,
verifying payload completeness, required fields, resolved links, resolved schema,
and content availability. Prevents unpopulated placeholders or broken content
from being published. No LLM calls.
"""

import re

from loguru import logger

from modules.workforce.workers.publisher_models import PlatformPayload
from modules.workforce.workers.seo_models import SEOOptimizedPackage


class PublishValidator:
    """Pre-publish readiness auditor for platform payloads.

    Audits:
    - Payload completeness (non-empty raw_content and formatted_payload).
    - Required fields (title, content, platform).
    - Resolved links (verifies internal/external links have valid resolved URLs).
    - Resolved schema (verifies no unpopulated {{PLACEHOLDER}} tags remain).
    - Content availability & metadata integrity.

    This validator is stateless. Each ``validate_readiness`` call produces
    fresh results from the provided inputs.
    """

    PLACEHOLDER_PATTERN: re.Pattern = re.compile(r"\{\{[A-Z0-9_]+\}\}")

    def validate_readiness(
        self,
        payload: PlatformPayload,
        seo_pkg: SEOOptimizedPackage,
        resolved_schema: dict | None = None,
        resolved_internal: list[dict] | None = None,
        resolved_external: list[dict] | None = None,
    ) -> tuple[bool, list[str]]:
        """Audits payload readiness prior to executing publication.

        Args:
            payload: PlatformPayload built by PayloadBuilder.
            seo_pkg: Source SEOOptimizedPackage.
            resolved_schema: Resolved schema dictionary.
            resolved_internal: Resolved internal links list.
            resolved_external: Resolved external links list.

        Returns:
            Tuple of:
            - is_valid (bool): True if payload is completely ready for publication.
            - validation_errors (list[str]): Diagnostic error messages.
        """
        errors: list[str] = []

        self._check_payload_completeness(payload, errors)
        self._check_required_fields(seo_pkg, errors)
        self._check_resolved_links(resolved_internal, resolved_external, errors)
        self._check_resolved_schema(resolved_schema or seo_pkg.schema_markup, errors)
        self._check_platform_constraints(payload, errors)

        is_valid = len(errors) == 0
        logger.info(
            f"PublishValidator: platform='{payload.platform}', is_valid={is_valid}, "
            f"errors={len(errors)}"
        )
        return is_valid, errors

    def _check_payload_completeness(self, payload: PlatformPayload, errors: list[str]) -> None:
        """Verifies payload is non-empty and has target platform.

        Args:
            payload: PlatformPayload.
            errors: Mutable error list.
        """
        if not payload.platform or not payload.platform.strip():
            errors.append("PlatformPayload missing required platform identifier.")
        if not payload.raw_content or not payload.raw_content.strip():
            errors.append("PlatformPayload raw_content is empty.")
        if not payload.formatted_payload:
            errors.append("PlatformPayload formatted_payload is empty.")

    def _check_required_fields(self, seo_pkg: SEOOptimizedPackage, errors: list[str]) -> None:
        """Verifies title and content exist in SEOOptimizedPackage.

        Args:
            seo_pkg: SEOOptimizedPackage.
            errors: Mutable error list.
        """
        if not seo_pkg.title or not seo_pkg.title.strip():
            errors.append("SEOOptimizedPackage title is empty.")
        if not seo_pkg.optimized_content or not seo_pkg.optimized_content.strip():
            errors.append("SEOOptimizedPackage optimized_content is empty.")

    def _check_resolved_links(
        self,
        internal_links: list[dict] | None,
        external_links: list[dict] | None,
        errors: list[str],
    ) -> None:
        """Verifies all links have non-empty resolved_url.

        Args:
            internal_links: List of internal link dicts.
            external_links: List of external link dicts.
            errors: Mutable error list.
        """
        if internal_links:
            for link in internal_links:
                url = link.get("resolved_url", "")
                if not url or not url.strip():
                    errors.append(
                        f"Internal link for topic '{link.get('target_topic')}' lacks resolved_url."
                    )
        if external_links:
            for link in external_links:
                url = link.get("resolved_url", "")
                if not url or not url.strip():
                    errors.append(
                        f"External link for topic '{link.get('target_topic')}' lacks resolved_url."
                    )

    def _check_resolved_schema(self, schema: dict, errors: list[str]) -> None:
        """Verifies schema contains no unpopulated {{PLACEHOLDER}} tags.

        Args:
            schema: Schema markup dictionary.
            errors: Mutable error list.
        """
        schema_str = str(schema)
        matches = self.PLACEHOLDER_PATTERN.findall(schema_str)
        if matches:
            errors.append(
                f"Schema markup contains unpopulated placeholders: {', '.join(set(matches))}."
            )

    def _check_platform_constraints(self, payload: PlatformPayload, errors: list[str]) -> None:
        """Validates platform-specific constraints (e.g. single X post character limit).

        Args:
            payload: PlatformPayload.
            errors: Mutable error list.
        """
        if payload.platform.lower() == "x":
            mode = payload.formatted_payload.get("mode", "single")
            posts = payload.formatted_payload.get("posts", [])
            if mode == "single" and posts:
                first_post = posts[0]
                if len(first_post) > 280:
                    errors.append(
                        f"Single X post exceeds 280 character limit ({len(first_post)} chars)."
                    )
