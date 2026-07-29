"""Prompt builder module for Writer Worker subsystem.

Constructs structured prompts for GeminiWebAdapter by injecting ContentBrief constraints
and Memory ContextPackage inputs.
"""


from loguru import logger

from modules.memory.models import ContextPackage
from modules.workforce.workers.brief_models import ContentBrief
from modules.workforce.workers.draft_models import WritingStyle


class PromptBuilder:
    """Builds structured system and generation prompts for GeminiWebAdapter."""

    PROMPT_VERSION: str = "v1.0.0"

    def build_prompt(
        self, brief: ContentBrief, context: ContextPackage | None = None
    ) -> str:
        """Constructs a comprehensive generation prompt.

        Args:
            brief: ContentBrief specification model.
            context: Optional ContextPackage memory context.

        Returns:
            str: Formatted prompt string for Gemini Web Adapter.
        """
        logger.info(f"PromptBuilder constructing prompt for brief '{brief.title_idea}' [{brief.platform}]")

        # Map brief tone string to WritingStyle enum
        style_enum = WritingStyle.AUTHORITATIVE
        if brief.tone:
            tone_str = brief.tone.upper()
            for s in WritingStyle:
                if s.value in tone_str:
                    style_enum = s
                    break

        outline_str = "\n".join([f"- {item}" for item in brief.outline]) if brief.outline else "- Introduction\n- Key Insights\n- Conclusion"
        keywords_str = ", ".join(brief.seo_keywords) if brief.seo_keywords else "N/A"

        citations_str = ""
        if brief.supporting_citations:
            citations_str = "\nRequired Citations to Include:\n" + "\n".join(
                [f"- {c.get('title', 'Ref')}: {c.get('url', '')}" for c in brief.supporting_citations]
            )

        context_str = ""
        if context and context.knowledge_memories:
            context_str = "\nKey Knowledge Facts:\n" + "\n".join(
                [f"- {mem.content[:150]}" for mem in context.knowledge_memories[:5]]
            )

        prompt = f"""You are an expert content writer for AI Content OS.

Generate a production-ready draft based strictly on the following brief:

Title Idea: {brief.title_idea}
Target Platform: {brief.platform}
Format Structure: {brief.content_format}
Audience: {brief.audience} ({brief.complexity})
Writing Style / Tone: {style_enum.value} ({brief.tone})
Estimated Length: {brief.estimated_length}
SEO Keywords: {keywords_str}

Opening Hook Strategy:
{brief.hook_strategy}

Required Section Outline:
{outline_str}
{context_str}
{citations_str}

Call to Action:
{brief.call_to_action}

Writing Guidelines:
1. Output valid Markdown formatting with clear section headings.
2. Maintain an authentic {style_enum.value} tone suitable for {brief.audience}.
3. Include all required section outline points.
4. Conclude with the explicit Call to Action.
"""
        return prompt
