"""Draft validator module for Writer Worker subsystem.

Evaluates generated markdown drafts against word count bounds, outline coverage,
citation preservation, and call-to-action compliance.
"""


from loguru import logger

from modules.workforce.workers.brief_models import ContentBrief
from modules.workforce.workers.draft_models import DraftValidationScores


class DraftValidator:
    """Audits draft quality and exposes fine-grained validation scores."""

    def __init__(
        self,
        min_words: int = 50,
        max_words: int = 4000,
        minimum_composite_threshold: float = 0.60,
    ):
        self.min_words: int = min_words
        self.max_words: int = max_words
        self.minimum_composite_threshold: float = minimum_composite_threshold

    def validate_draft(
        self, draft: str, brief: ContentBrief
    ) -> tuple[bool, DraftValidationScores, list[str]]:
        """Audits generated draft content against brief requirements.

        Args:
            draft: Markdown text draft.
            brief: ContentBrief specification.

        Returns:
            Tuple[bool, DraftValidationScores, List[str]]: Validation pass flag, scores model, and list of issues.
        """
        issues: list[str] = []
        if not draft or not draft.strip():
            return False, DraftValidationScores(
                length_score=0.0, citation_score=0.0, outline_score=0.0, cta_score=0.0, composite_score=0.0
            ), ["Empty draft text"]

        words = draft.split()
        word_count = len(words)

        # 1. Length Score
        if word_count < self.min_words:
            length_score = round(word_count / self.min_words, 2)
            issues.append(f"Draft too short ({word_count} words < {self.min_words} min)")
        elif word_count > self.max_words:
            length_score = 0.80
            issues.append(f"Draft exceeds recommended max length ({word_count} words)")
        else:
            length_score = 1.0

        # 2. Outline Section Score
        outline_matches = 0
        if brief.outline:
            for item in brief.outline:
                # Extract key heading words
                key_term = item.split(":")[0].replace("1.", "").replace("2.", "").replace("3.", "").replace("4.", "").strip().lower()
                if key_term and key_term in draft.lower():
                    outline_matches += 1
            outline_score = round(outline_matches / len(brief.outline), 2)
            if outline_score < 0.5:
                issues.append(f"Outline section coverage low ({outline_matches}/{len(brief.outline)})")
        else:
            outline_score = 1.0

        # 3. Citation Preservation Score
        citation_matches = 0
        if brief.supporting_citations:
            for c in brief.supporting_citations:
                url = c.get("url", "")
                title = c.get("title", "")
                if (url and url in draft) or (title and title.lower() in draft.lower()):
                    citation_matches += 1
            citation_score = round(citation_matches / len(brief.supporting_citations), 2)
            if citation_score < 0.5:
                issues.append(f"Citation preservation low ({citation_matches}/{len(brief.supporting_citations)})")
        else:
            citation_score = 1.0

        # 4. CTA Presence Score
        cta_score = 1.0
        if brief.call_to_action:
            cta_words = [w.lower() for w in brief.call_to_action.split() if len(w) > 3]
            matches = sum(1 for w in cta_words if w in draft.lower())
            if matches == 0:
                cta_score = 0.5
                issues.append("Call to action missing or not prominent in concluding section")

        composite_score = round((length_score * 0.25) + (outline_score * 0.35) + (citation_score * 0.25) + (cta_score * 0.15), 2)

        scores = DraftValidationScores(
            length_score=length_score,
            citation_score=citation_score,
            outline_score=outline_score,
            cta_score=cta_score,
            composite_score=composite_score,
        )

        is_valid = composite_score >= self.minimum_composite_threshold
        if not is_valid:
            logger.warning(f"Draft failed quality validation [Score: {composite_score} < {self.minimum_composite_threshold}]")
        else:
            logger.info(f"Draft validated successfully [Composite Score: {composite_score}]")

        return is_valid, scores, issues
