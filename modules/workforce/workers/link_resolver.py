"""Link Resolver module for Publisher Worker subsystem.

Deterministically resolves internal and external target_topic suggestions
produced by the SEO Worker into live, canonical URLs using a configurable
route map and base domain. Makes zero network requests.
"""

from loguru import logger

from modules.workforce.workers.seo_models import SEOOptimizedPackage


class LinkResolver:
    """Deterministic link resolver converting topic targets to URLs.

    Maps ``target_topic`` placeholders in ``internal_link_suggestions`` and
    ``external_link_suggestions`` to resolved URLs using explicit route tables
    or deterministic fallback patterns. Zero network requests are made.

    This resolver is stateless and deterministic.
    """

    DEFAULT_BASE_DOMAIN: str = "https://example.com"

    def __init__(
        self,
        route_map: dict[str, str] | None = None,
        base_domain: str | None = None,
    ) -> None:
        """Initializes LinkResolver with custom route mapping and base domain.

        Args:
            route_map: Optional mapping dictionary of {target_topic: resolved_url}.
            base_domain: Default base domain for internal topic resolution.
        """
        self.route_map: dict[str, str] = route_map or {}
        self.base_domain: str = (base_domain or self.DEFAULT_BASE_DOMAIN).rstrip("/")

    def resolve_links(
        self,
        seo_pkg: SEOOptimizedPackage,
        custom_route_map: dict[str, str] | None = None,
        base_domain: str | None = None,
    ) -> tuple[list[dict], list[dict], int]:
        """Resolves internal and external link suggestions from SEOOptimizedPackage.

        Args:
            seo_pkg: SEOOptimizedPackage containing link suggestions.
            custom_route_map: Optional task-specific route map overrides.
            base_domain: Optional base domain override.

        Returns:
            Tuple of:
            - Resolved internal links list [{anchor_text, target_topic, resolved_url, rationale}]
            - Resolved external links list [{anchor_text, target_topic, resolved_url, rationale}]
            - Total resolution count (int)
        """
        active_route_map = {**self.route_map, **(custom_route_map or {})}
        domain = (base_domain or self.base_domain).rstrip("/")

        resolved_internal: list[dict] = []
        for item in seo_pkg.internal_link_suggestions:
            resolved_internal.append(
                self._resolve_single_link(item, is_internal=True, route_map=active_route_map, domain=domain)
            )

        resolved_external: list[dict] = []
        for item in seo_pkg.external_link_suggestions:
            resolved_external.append(
                self._resolve_single_link(item, is_internal=False, route_map=active_route_map, domain=domain)
            )

        total_count = len(resolved_internal) + len(resolved_external)
        logger.info(
            f"LinkResolver: resolved {len(resolved_internal)} internal and "
            f"{len(resolved_external)} external links (total={total_count})."
        )
        return resolved_internal, resolved_external, total_count

    def _resolve_single_link(
        self,
        item: dict,
        is_internal: bool,
        route_map: dict[str, str],
        domain: str,
    ) -> dict:
        """Resolves a single link suggestion dictionary.

        Args:
            item: Suggestion dict with anchor_text, target_topic, rationale.
            is_internal: Whether this link is internal or external.
            route_map: Route mapping table.
            domain: Base domain for internal resolution.

        Returns:
            Resolved link dictionary containing ``resolved_url``.
        """
        anchor_text = item.get("anchor_text", "")
        target_topic = item.get("target_topic", "").strip()
        rationale = item.get("rationale", "")

        # 1. Check explicit route map
        if target_topic in route_map:
            resolved_url = route_map[target_topic]
        elif target_topic.startswith("http://") or target_topic.startswith("https://"):
            resolved_url = target_topic
        elif is_internal:
            # Fallback for internal: base_domain/slugified-topic
            slug = target_topic.lower().replace(" ", "-")
            resolved_url = f"{domain}/{slug}"
        else:
            # Fallback for external: https://target_topic.org or search link
            slug = target_topic.lower().replace(" ", "-")
            resolved_url = f"https://{slug}.org"

        return {
            "anchor_text": anchor_text,
            "target_topic": target_topic,
            "resolved_url": resolved_url,
            "rationale": rationale,
        }
