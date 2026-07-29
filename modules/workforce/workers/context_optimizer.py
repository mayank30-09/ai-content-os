"""Context optimizer module for Memory Worker subsystem.

Leverages ContextBuilder to build role-tailored, prioritized ContextPackage payloads for
downstream workers (Content Strategist, Writer, Fact Checker, Editor, SEO Worker).
"""


from loguru import logger

from modules.memory.context_builder import ContextBuilder
from modules.memory.manager import MemoryManager, memory_manager
from modules.memory.models import ContextPackage


class ContextOptimizer:
    """Optimizes ContextPackages for specific target worker roles."""

    def __init__(
        self,
        memory_mgr: MemoryManager | None = None,
        builder: ContextBuilder | None = None,
    ):
        self.memory_manager: MemoryManager = memory_mgr or memory_manager
        self.builder: ContextBuilder = builder or ContextBuilder(manager=self.memory_manager)

    def optimize_for_role(
        self, topic: str, target_role: str = "writer", max_items: int = 20
    ) -> ContextPackage:
        """Builds a role-tailored, prioritized ContextPackage.

        Args:
            topic: Target topic string.
            target_role: Target downstream worker role e.g. writer, fact_checker, strategist, editor, seo.
            max_items: Maximum items allowed per namespace.

        Returns:
            ContextPackage: Tailored ContextPackage payload.
        """
        role_lower = target_role.lower()
        logger.info(f"Optimizing ContextPackage for role '{target_role}' on topic '{topic}'")

        # Base context package from ContextBuilder
        base_package = self.builder.build_context_package(topic=topic)

        if "fact" in role_lower or "checker" in role_lower:
            # Fact Checker: Prioritize Knowledge & Research citations
            return ContextPackage(
                topic=topic,
                research_memories=base_package.research_memories[:max_items],
                knowledge_memories=base_package.knowledge_memories[:max_items],
                style_memories=[],
                prompt_memories=[],
                generation_memories=[],
            )

        elif "strategist" in role_lower or "plan" in role_lower:
            # Content Strategist: Prioritize Research & Generation history
            return ContextPackage(
                topic=topic,
                research_memories=base_package.research_memories[:max_items],
                knowledge_memories=base_package.knowledge_memories[:max_items],
                style_memories=base_package.style_memories[:5],
                prompt_memories=[],
                generation_memories=base_package.generation_memories[:max_items],
            )

        elif "editor" in role_lower or "review" in role_lower:
            # Editor: Prioritize Style rules & Previous Generations
            return ContextPackage(
                topic=topic,
                research_memories=[],
                knowledge_memories=base_package.knowledge_memories[:5],
                style_memories=base_package.style_memories[:max_items],
                prompt_memories=[],
                generation_memories=base_package.generation_memories[:max_items],
            )

        elif "seo" in role_lower:
            # SEO Worker: Prioritize Research & Knowledge keywords
            return ContextPackage(
                topic=topic,
                research_memories=base_package.research_memories[:max_items],
                knowledge_memories=base_package.knowledge_memories[:max_items],
                style_memories=[],
                prompt_memories=[],
                generation_memories=[],
            )

        # Default Writer context (all namespaces included)
        return ContextPackage(
            topic=topic,
            research_memories=base_package.research_memories[:max_items],
            knowledge_memories=base_package.knowledge_memories[:max_items],
            style_memories=base_package.style_memories[:max_items],
            prompt_memories=base_package.prompt_memories[:max_items],
            generation_memories=base_package.generation_memories[:max_items],
        )
