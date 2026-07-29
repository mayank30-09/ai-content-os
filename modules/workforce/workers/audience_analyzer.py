"""Audience analyzer module for Content Strategist subsystem.

Classifies target audience categories, technical complexity levels, and tone specs.
"""


from loguru import logger

from modules.research.models import ResearchPackage


class AudienceAnalyzer:
    """Classifies target audience intent, conceptual depth, and recommended tone."""

    AUDIENCE_CATEGORIES = [
        "Beginner",
        "Intermediate",
        "Advanced",
        "Founder",
        "Developer",
        "Student",
        "Enterprise",
        "Creator",
    ]

    def classify_audience(
        self, topic: str, package: ResearchPackage | None = None
    ) -> tuple[str, str, str]:
        """Classifies target audience, technical complexity level, and recommended tone.

        Args:
            topic: Strategy topic string.
            package: Optional ResearchPackage context.

        Returns:
            Tuple[str, str, str]: (audience_category, complexity_level, tone_specification)
        """
        text_corpus = (topic + " " + (package.executive_summary if package else "")).lower()

        # Keyword heuristics
        if any(w in text_corpus for w in ["founder", "startup", "revenue", "roi", "business"]):
            return "Founder", "High Level", "Strategic & Executive"
        elif any(w in text_corpus for w in ["code", "fastapi", "api", "python", "developer", "architecture"]):
            return "Developer", "Intermediate", "Technical & Practical"
        elif any(w in text_corpus for w in ["enterprise", "compliance", "security", "scale"]):
            return "Enterprise", "Advanced", "Formal & Authoritative"
        elif any(w in text_corpus for w in ["beginner", "101", "intro", "basics", "simple"]):
            return "Beginner", "Foundational", "Accessible & Encouraging"
        elif any(w in text_corpus for w in ["student", "learn", "study"]):
            return "Student", "Foundational", "Educational & Clear"
        elif any(w in text_corpus for w in ["creator", "youtube", "instagram", "audience", "social"]):
            return "Creator", "Practical", "Engaging & Actionable"

        # Default fallback
        logger.info(f"Using default 'Intermediate' Developer classification for topic '{topic}'")
        return "Developer", "Intermediate", "Authoritative & Insightful"
