"""Payload Builder module for Publisher Worker subsystem.

Uses the Strategy Pattern to build platform-specific publication payloads
(e.g. LinkedIn, X/Twitter, and future CMS platforms like Medium, Dev.to, Ghost, WordPress, Substack).
"""

from abc import ABC, abstractmethod

from loguru import logger

from modules.workforce.workers.publisher_models import PlatformPayload
from modules.workforce.workers.seo_models import SEOOptimizedPackage


class BasePayloadStrategy(ABC):
    """Abstract interface for platform-specific payload strategies."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Target platform name identifier."""
        pass

    @abstractmethod
    def build(
        self,
        seo_pkg: SEOOptimizedPackage,
        content: str,
        schema: dict,
    ) -> PlatformPayload:
        """Builds a PlatformPayload for the strategy's target platform.

        Args:
            seo_pkg: Source SEOOptimizedPackage.
            content: Content with resolved links.
            schema: Resolved schema markup dictionary.

        Returns:
            PlatformPayload model.
        """
        pass


class LinkedInPayloadStrategy(BasePayloadStrategy):
    """Payload strategy for LinkedIn web and API publishing."""

    @property
    def platform_name(self) -> str:
        return "linkedin"

    def build(
        self,
        seo_pkg: SEOOptimizedPackage,
        content: str,
        schema: dict,
    ) -> PlatformPayload:
        headline = seo_pkg.title
        body = content

        # Format hashtags from focus + secondary keywords
        hashtags = [f"#{kw.replace(' ', '')}" for kw in [seo_pkg.focus_keyword] + seo_pkg.secondary_keywords if kw]
        hashtag_str = " ".join(hashtags) if hashtags else ""

        full_post = f"{headline}\n\n{body}"
        if hashtag_str:
            full_post += f"\n\n{hashtag_str}"

        formatted_payload = {
            "author": schema.get("author", "AI Content OS"),
            "commentary": full_post,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "article": {
                    "source": schema.get("url", "https://example.com"),
                    "title": seo_pkg.meta_title or headline,
                    "description": seo_pkg.meta_description,
                }
            },
        }

        return PlatformPayload(
            platform="linkedin",
            raw_content=full_post,
            formatted_payload=formatted_payload,
            target_channels=["feed"],
            metadata={"visibility": "PUBLIC", "hashtag_count": len(hashtags)},
        )


class XPayloadStrategy(BasePayloadStrategy):
    """Payload strategy for X (Twitter) publishing."""

    MAX_TWEET_CHARS: int = 280

    @property
    def platform_name(self) -> str:
        return "x"

    def build(
        self,
        seo_pkg: SEOOptimizedPackage,
        content: str,
        schema: dict,
    ) -> PlatformPayload:
        # Determine single tweet vs thread
        posts = self._split_into_thread(seo_pkg.title, content, seo_pkg.focus_keyword)

        formatted_payload = {
            "mode": "thread" if len(posts) > 1 else "single",
            "posts": posts,
            "reply_settings": "everyone",
        }

        return PlatformPayload(
            platform="x",
            raw_content="\n---\n".join(posts),
            formatted_payload=formatted_payload,
            target_channels=["timeline"],
            metadata={"thread_length": len(posts), "character_limit": self.MAX_TWEET_CHARS},
        )

    def _split_into_thread(self, title: str, content: str, keyword: str) -> list[str]:
        """Splits content into <=280 character posts for an X thread.

        Args:
            title: Post title.
            content: Main text content.
            keyword: Focus keyword.

        Returns:
            List of tweet strings.
        """
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        posts: list[str] = []

        # Post 1: Title + Hook
        hook = f"🧵 {title}"
        if keyword and f"#{keyword}" not in hook:
            hook += f" #{keyword.replace(' ', '')}"
        posts.append(hook[: self.MAX_TWEET_CHARS])

        # Subsequent posts from paragraphs
        current_post = ""
        for p in paragraphs:
            # Strip markdown headers
            clean_p = p.lstrip("# ").strip()
            if len(clean_p) > self.MAX_TWEET_CHARS:
                clean_p = clean_p[: self.MAX_TWEET_CHARS - 3] + "..."

            if len(current_post) + len(clean_p) + 2 <= self.MAX_TWEET_CHARS:
                current_post = f"{current_post}\n\n{clean_p}".strip()
            else:
                if current_post:
                    posts.append(current_post[: self.MAX_TWEET_CHARS])
                current_post = clean_p

        if current_post and current_post not in posts:
            posts.append(current_post[: self.MAX_TWEET_CHARS])

        return posts[:10]  # Cap thread at 10 posts max


class GenericCMSPayloadStrategy(BasePayloadStrategy):
    """Fallback strategy for generic CMS, Medium, Ghost, Dev.to, Hashnode, WordPress."""

    def __init__(self, platform_name: str = "generic_cms") -> None:
        self._platform_name = platform_name

    @property
    def platform_name(self) -> str:
        return self._platform_name

    def build(
        self,
        seo_pkg: SEOOptimizedPackage,
        content: str,
        schema: dict,
    ) -> PlatformPayload:
        formatted_payload = {
            "title": seo_pkg.title,
            "body_markdown": content,
            "slug": seo_pkg.slug,
            "meta_title": seo_pkg.meta_title,
            "meta_description": seo_pkg.meta_description,
            "tags": [seo_pkg.focus_keyword] + seo_pkg.secondary_keywords,
            "schema_json_ld": schema,
        }
        return PlatformPayload(
            platform=self._platform_name,
            raw_content=content,
            formatted_payload=formatted_payload,
            metadata={"format": "markdown"},
        )


class PayloadBuilder:
    """Strategy engine for constructing platform-specific publication payloads.

    Supports extensible platform strategies via ``register_strategy``.
    Includes built-in support for LinkedIn and X (Twitter), plus fallback generic CMS.
    """

    def __init__(self) -> None:
        self.strategies: dict[str, BasePayloadStrategy] = {}
        # Register built-in strategies
        self.register_strategy(LinkedInPayloadStrategy())
        self.register_strategy(XPayloadStrategy())

    def register_strategy(self, strategy: BasePayloadStrategy) -> None:
        """Registers a platform strategy instance.

        Args:
            strategy: BasePayloadStrategy implementation.
        """
        self.strategies[strategy.platform_name.lower()] = strategy
        logger.debug(f"PayloadBuilder registered strategy for '{strategy.platform_name}'")

    def build_payload(
        self,
        platform: str,
        seo_pkg: SEOOptimizedPackage,
        content: str,
        schema: dict,
    ) -> PlatformPayload:
        """Builds a platform payload using the matching registered strategy.

        Args:
            platform: Platform name identifier (e.g. linkedin, x, medium, ghost).
            seo_pkg: Source SEOOptimizedPackage.
            content: Content with resolved links.
            schema: Resolved schema markup dictionary.

        Returns:
            PlatformPayload instance.
        """
        platform_key = platform.lower().strip()
        strategy = self.strategies.get(platform_key)

        if not strategy:
            logger.info(
                f"PayloadBuilder: No specific strategy for '{platform_key}'. "
                f"Using generic CMS payload strategy."
            )
            strategy = GenericCMSPayloadStrategy(platform_name=platform_key)

        payload = strategy.build(seo_pkg, content, schema)
        logger.info(
            f"PayloadBuilder: constructed '{platform_key}' payload "
            f"(size={len(payload.raw_content)} chars)."
        )
        return payload
