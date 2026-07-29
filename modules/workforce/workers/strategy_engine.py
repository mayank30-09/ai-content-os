"""Strategy engine module for Content Strategist subsystem.

Synthesizes research and memory inputs into strongly-typed ContentBrief objects.
"""


from loguru import logger

from modules.memory.models import ContextPackage
from modules.research.models import ResearchPackage
from modules.workforce.workers.audience_analyzer import AudienceAnalyzer
from modules.workforce.workers.brief_models import (
    ContentBrief,
    ContentCalendarHint,
    ContentObjective,
    ContentPriority,
)
from modules.workforce.workers.platform_selector import PlatformSelector
from modules.workforce.workers.strategist_metrics import ContentStrategistMetrics


class StrategyEngine:
    """Synthesizes strategy briefs from research packages and memory context."""

    def __init__(
        self,
        audience_analyzer: AudienceAnalyzer | None = None,
        platform_selector: PlatformSelector | None = None,
    ):
        self.audience_analyzer: AudienceAnalyzer = audience_analyzer or AudienceAnalyzer()
        self.platform_selector: PlatformSelector = platform_selector or PlatformSelector()

    def generate_brief(
        self,
        topic: str,
        goal: ContentObjective = ContentObjective.EDUCATIONAL,
        priority: ContentPriority = ContentPriority.MEDIUM,
        package: ResearchPackage | None = None,
        context: ContextPackage | None = None,
    ) -> ContentBrief:
        """Synthesizes a complete ContentBrief blueprint.

        Args:
            topic: Core topic or headline string.
            goal: ContentObjective strategic goal.
            priority: Production ContentPriority level.
            package: Optional ResearchPackage from research worker.
            context: Optional ContextPackage from memory worker.

        Returns:
            ContentBrief: Fully populated brief payload.
        """
        logger.info(f"StrategyEngine generating ContentBrief for topic: '{topic}' [Goal: {goal.value}]")

        # 1. Analyze Audience & Tone
        audience, complexity, tone = self.audience_analyzer.classify_audience(topic=topic, package=package)

        # 2. Select Platform & Format
        platform, content_format, repurpose_list = self.platform_selector.select_platform(goal=goal, audience=audience)

        # Extract citations & key points from research package if present
        citations: list[dict] = []
        key_points: list[str] = []
        if package:
            key_points = package.key_facts[:5] if package.key_facts else [f"Overview of {topic}"]
            for doc in package.ranked_documents[:3]:
                citations.append({
                    "title": doc.title,
                    "url": doc.url,
                    "source": doc.source,
                    "confidence": doc.confidence,
                })
        else:
            key_points = [f"Introduction to {topic}", f"Key benefits of {topic}", f"Implementation guide for {topic}"]

        # Build section outline
        outline = [
            f"1. Executive Hook: Why {topic} matters for {audience}",
            f"2. Core Concepts: Key insights and framework for {topic}",
            "3. Deep Dive: Implementation steps and best practices",
            "4. Takeaways: Practical conclusions and call to action",
        ]

        calendar_hint = ContentCalendarHint(
            publish_priority=priority,
            recommended_day="Tuesday" if priority in [ContentPriority.HIGH, ContentPriority.URGENT] else "Thursday",
            recommended_time_window="09:00 - 11:00 EST",
            evergreen_score=0.85 if goal == ContentObjective.EDUCATIONAL else 0.60,
            trend_score=0.80 if goal == ContentObjective.VIRAL_AWARENESS else 0.40,
        )

        brief = ContentBrief(
            title_idea=f"Mastering {topic}: A Guide for {audience}s",
            content_goal=goal,
            priority=priority,
            estimated_effort="1-2 hours" if content_format in ["Thread", "Carousel"] else "half-day",
            audience=audience,
            platform=platform,
            content_format=content_format,
            tone=tone,
            complexity=complexity,
            estimated_length="1200-1500 words" if platform in ["Blog", "Newsletter"] else "8-10 slides / 6-8 tweets",
            hook_strategy=f"Start with a strong statistic or common pain point regarding {topic}.",
            outline=outline,
            key_points=key_points,
            supporting_citations=citations,
            seo_keywords=[topic.lower(), f"{topic.lower()} guide", f"best {topic.lower()} practices"],
            call_to_action=f"Subscribe and share for more insights on {topic}.",
            repurpose_to=repurpose_list,
            calendar_hint=calendar_hint,
            risks=["Ensure technical terminology is aligned with audience complexity level."],
            confidence=0.90,
        )

        return brief

    def compute_metrics(
        self, brief: ContentBrief, package: ResearchPackage | None = None
    ) -> ContentStrategistMetrics:
        """Calculates strategy telemetry metrics for the generated brief.

        Args:
            brief: ContentBrief instance.
            package: ResearchPackage input.

        Returns:
            ContentStrategistMetrics: Strategy execution metrics.
        """
        doc_count = len(package.ranked_documents) if package and package.ranked_documents else 0
        citation_count = len(brief.supporting_citations)
        res_cov = min(1.0, round(citation_count / doc_count, 2)) if doc_count > 0 else 0.0

        return ContentStrategistMetrics(
            audience_confidence=0.90,
            platform_confidence=0.90,
            format_confidence=0.85,
            strategy_score=round((0.90 + 0.90 + 0.85) / 3, 2),
            research_coverage=res_cov,
            citation_coverage=1.0 if citation_count > 0 else 0.0,
            briefs_generated=1,
        )
