"""ContextBuilder module for Intelligent Memory System.

Assembles ContextPackage payloads containing research, knowledge, style, prompt, and
generation history memories for injection into AI generation prompts.
"""


from loguru import logger

from modules.memory.manager import MemoryManager, memory_manager
from modules.memory.models import (
    ContextPackage,
    GenerationMemory,
    KnowledgeMemory,
    MemoryNamespace,
    PromptMemory,
    ResearchMemory,
    StyleMemory,
)


class ContextBuilder:
    """Assembles structured ContextPackage payloads across memory namespaces."""

    def __init__(self, manager: MemoryManager | None = None):
        self.manager: MemoryManager = manager or memory_manager

    def build_context_package(
        self, topic: str, max_items_per_namespace: int = 5
    ) -> ContextPackage:
        """Collects the top ranked relevant memories across all namespaces for a topic.

        Args:
            topic: Content generation topic string.
            max_items_per_namespace: Maximum items to include per namespace.

        Returns:
            ContextPackage: Structured context package ready for prompt rendering.
        """
        logger.info(f"Building ContextPackage for topic: '{topic}'")

        # 1. Retrieve Research Memories
        res_records = self.manager.search_memory(
            topic, namespace=MemoryNamespace.RESEARCH, limit=max_items_per_namespace
        )
        research_mems = [r for r in res_records if isinstance(r, ResearchMemory)]

        # 2. Retrieve Knowledge Memories
        knw_records = self.manager.search_memory(
            topic, namespace=MemoryNamespace.KNOWLEDGE, limit=max_items_per_namespace
        )
        knowledge_mems = [k for k in knw_records if isinstance(k, KnowledgeMemory)]

        # 3. Retrieve Style Memories
        style_records = self.manager.get_by_namespace(
            MemoryNamespace.STYLE, limit=max_items_per_namespace
        )
        style_mems = [s for s in style_records if isinstance(s, StyleMemory)]

        # 4. Retrieve Prompt Memories
        prompt_records = self.manager.get_by_namespace(
            MemoryNamespace.PROMPT, limit=max_items_per_namespace
        )
        prompt_mems = [p for p in prompt_records if isinstance(p, PromptMemory)]

        # 5. Retrieve Generation History Memories
        gen_records = self.manager.search_memory(
            topic, namespace=MemoryNamespace.GENERATION, limit=max_items_per_namespace
        )
        generation_mems = [g for g in gen_records if isinstance(g, GenerationMemory)]

        package = ContextPackage(
            topic=topic,
            research_memories=research_mems,
            knowledge_memories=knowledge_mems,
            style_memories=style_mems,
            prompt_memories=prompt_mems,
            generation_memories=generation_mems,
        )

        logger.info(f"ContextPackage assembled successfully for topic: '{topic}'")
        return package

context_builder = ContextBuilder()
