"""Platform selector module for Content Strategist subsystem.

Maps strategic goals and audience targets to publishing platforms, format structures,
and cross-platform repurposing strategies.
"""


from loguru import logger

from modules.workforce.workers.brief_models import ContentObjective


class PlatformSelector:
    """Rules engine for platform, format, and repurposing recommendations."""

    SUPPORTED_PLATFORMS = [
        "LinkedIn",
        "X",
        "Instagram Carousel",
        "Instagram Reel",
        "Blog",
        "Newsletter",
    ]

    SUPPORTED_FORMATS = [
        "Tutorial",
        "Deep Dive",
        "Case Study",
        "Opinion",
        "Comparison",
        "Framework",
        "Checklist",
        "Thread",
        "Carousel",
        "Reel Script",
        "Blog",
    ]

    def select_platform(
        self, goal: ContentObjective, audience: str
    ) -> tuple[str, str, list[str]]:
        """Determines primary platform, primary format, and repurposing destinations.

        Args:
            goal: ContentObjective enum value.
            audience: Target audience category string.

        Returns:
            Tuple[str, str, List[str]]: (primary_platform, primary_format, repurpose_destinations)
        """
        if goal == ContentObjective.THOUGHT_LEADERSHIP or audience in ["Founder", "Enterprise"]:
            return "LinkedIn", "Framework", ["X Thread", "Newsletter Summary"]

        elif goal == ContentObjective.VIRAL_AWARENESS or audience == "Creator":
            return "X", "Thread", ["Instagram Carousel", "LinkedIn Post"]

        elif goal == ContentObjective.SEO_LEAD_GEN:
            return "Blog", "Tutorial", ["LinkedIn Article", "Newsletter"]

        elif goal == ContentObjective.PRODUCT_PROMOTION:
            return "Newsletter", "Case Study", ["LinkedIn Post", "X Post"]

        elif goal == ContentObjective.COMMUNITY_BUILDING:
            return "Instagram Carousel", "Carousel", ["X Thread"]

        # Default Educational fallback
        logger.info(f"Using default Educational LinkedIn platform mapping for goal '{goal}'")
        return "LinkedIn", "Deep Dive", ["X Thread", "Blog Post"]
