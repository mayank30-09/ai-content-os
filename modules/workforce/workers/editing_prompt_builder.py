"""Editing prompt builder for Editor Worker subsystem.

Assembles structured editing prompts for the GeminiWebProvider, embedding
the original draft, verified claims, citations, and SEO keywords with
explicit constraints to preserve factual accuracy while improving prose.
"""

from modules.workforce.workers.verification_models import VerificationReport, VerifiedDraftPackage


class EditingPromptBuilder:
    """Builds structured editing prompts for AI-assisted draft improvement.

    Produces prompts that instruct the language model to improve readability,
    grammar, transitions, flow, and style — while explicitly forbidding
    changes to facts, statistics, dates, citations, and SEO keywords.

    This builder is stateless. Each call produces a fresh prompt string.
    """

    PROMPT_VERSION: str = "v1.0.0"

    def build_system_instruction(self) -> str:
        """Returns the system-level persona instruction for the editing session.

        Returns:
            System instruction string for a professional copy editor persona.
        """
        return (
            "You are a professional copy editor with expertise in digital content. "
            "Your role is to improve the readability, grammar, flow, transitions, "
            "and style of the provided draft. "
            "You MUST NOT change any facts, statistics, numbers, dates, or quoted text. "
            "You MUST NOT remove or alter any citations or URLs. "
            "You MUST NOT add new facts or claims that are not in the original draft. "
            "You MUST preserve all SEO keywords naturally within the text. "
            "Return ONLY the improved markdown content. Do not include explanations."
        )

    def build_editing_prompt(self, verified_pkg: VerifiedDraftPackage) -> str:
        """Builds a structured editing prompt from a VerifiedDraftPackage.

        The prompt includes the full original draft, a list of verified claims
        that must not be altered, all citations that must be preserved, and
        SEO keywords that must remain present in the edited output.

        Args:
            verified_pkg: VerifiedDraftPackage from the Fact Checker Worker.

        Returns:
            Formatted editing prompt string.
        """
        draft_pkg = verified_pkg.draft_package
        report = verified_pkg.verification_report

        # Build verified claims constraint block
        verified_claims_block = self._build_claims_block(report)

        # Build citation preservation block
        citation_block = self._build_citation_block(draft_pkg.citations_used)

        # Build keyword preservation block
        keyword_block = self._build_keyword_block(draft_pkg.seo_keywords)

        return f"""## EDITING TASK

Edit the following draft to improve readability, grammar, flow, transitions, and style.

### CONSTRAINTS — DO NOT VIOLATE

1. DO NOT change any facts, statistics, numbers, or dates.
2. DO NOT remove or alter any citations or URLs.
3. DO NOT add new facts or claims not present in the original.
4. DO NOT change the overall structure or heading hierarchy.
5. Preserve all SEO keywords naturally in the text.

{verified_claims_block}
{citation_block}
{keyword_block}
### STYLE GUIDANCE

- Target writing style: {draft_pkg.writing_style.value}
- Target audience: {draft_pkg.audience}
- Target platform: {draft_pkg.platform}
- Content format: {draft_pkg.content_format}

### ORIGINAL DRAFT

{draft_pkg.draft}

### OUTPUT

Return ONLY the improved markdown content."""

    def _build_claims_block(self, report: VerificationReport) -> str:
        """Builds the verified claims constraint block.

        Args:
            report: VerificationReport containing claim results.

        Returns:
            Formatted constraint block string.
        """
        if not report.claim_results:
            return "### VERIFIED CLAIMS\n\nNo specific claims to preserve.\n"

        lines = ["### VERIFIED CLAIMS — MUST NOT BE ALTERED\n"]
        for i, claim in enumerate(report.claim_results, 1):
            lines.append(f"{i}. [{claim.status}] {claim.claim_text}")
        lines.append("")
        return "\n".join(lines)

    def _build_citation_block(self, citations: list[dict]) -> str:
        """Builds the citation preservation block.

        Args:
            citations: List of citation dicts from DraftPackage.citations_used.

        Returns:
            Formatted citation preservation block string.
        """
        if not citations:
            return "### CITATIONS — PRESERVE ALL\n\nNo citations to preserve.\n"

        lines = ["### CITATIONS — PRESERVE ALL\n"]
        for c in citations:
            url = c.get("url", "")
            title = c.get("title", "Untitled")
            lines.append(f"- [{title}]({url})")
        lines.append("")
        return "\n".join(lines)

    def _build_keyword_block(self, keywords: list[str]) -> str:
        """Builds the SEO keyword preservation block.

        Args:
            keywords: List of SEO keywords from DraftPackage.seo_keywords.

        Returns:
            Formatted keyword preservation block string.
        """
        if not keywords:
            return "### SEO KEYWORDS — PRESERVE ALL\n\nNo keywords specified.\n"

        keyword_str = ", ".join(keywords)
        return f"### SEO KEYWORDS — PRESERVE ALL\n\n{keyword_str}\n"
