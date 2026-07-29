"""Citation verifier for Fact Checker Worker subsystem.

Audits citation lists from DraftPackage against ResearchPackage source documents,
detecting missing, duplicate, and unmappable citations.
"""

from dataclasses import dataclass

from loguru import logger

from modules.research.models import ResearchPackage

# ---------------------------------------------------------------------------
# Citation audit result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CitationAuditResult:
    """Immutable result of a single citation audit evaluation.

    Attributes:
        url: Citation URL being audited.
        title: Citation title if present.
        status: Outcome: ``matched``, ``unmatched``, or ``duplicate``.
        matched_document_title: Title of matched ResearchDocument, if found.
    """

    url: str
    title: str
    status: str
    matched_document_title: str | None = None


class CitationVerifier:
    """Verifies draft citations against ResearchPackage source documents.

    Performs three checks:
    - **Existence**: Whether each cited URL appears in the research source list.
    - **Duplication**: Whether duplicate citation URLs are present in the draft.
    - **Mapping**: Whether citations map to known research document titles.

    This verifier is stateless — all inputs are consumed per ``verify_citations`` call.
    """

    def verify_citations(
        self,
        citations_used: list[dict],
        research_package: ResearchPackage | None,
    ) -> tuple[list[CitationAuditResult], int]:
        """Audits citations from a DraftPackage against a ResearchPackage.

        Args:
            citations_used: List of citation dicts from DraftPackage.citations_used.
                Expected dict keys: ``url`` (str), ``title`` (str, optional).
            research_package: ResearchPackage containing ranked_documents.

        Returns:
            Tuple of:
            - List of CitationAuditResult entries for each citation.
            - Count of duplicate citations detected.
        """
        if not citations_used:
            logger.debug("CitationVerifier: no citations to verify.")
            return [], 0

        # Build URL lookup index from research documents
        source_urls: set[str] = set()
        source_title_map: dict[str, str] = {}
        if research_package and research_package.ranked_documents:
            for doc in research_package.ranked_documents:
                if doc.url:
                    normalized = self._normalize_url(doc.url)
                    source_urls.add(normalized)
                    source_title_map[normalized] = doc.title

        results: list[CitationAuditResult] = []
        seen_urls: set[str] = set()
        duplicate_count = 0

        for citation in citations_used:
            raw_url = citation.get("url", "")
            title = citation.get("title", "")

            if not raw_url:
                # Malformed citation — no URL at all
                results.append(CitationAuditResult(
                    url="",
                    title=title,
                    status="unmatched",
                    matched_document_title=None,
                ))
                continue

            normalized_url = self._normalize_url(raw_url)

            # Duplicate detection
            if normalized_url in seen_urls:
                duplicate_count += 1
                results.append(CitationAuditResult(
                    url=raw_url,
                    title=title,
                    status="duplicate",
                    matched_document_title=source_title_map.get(normalized_url),
                ))
                logger.debug(f"CitationVerifier: duplicate citation detected: '{raw_url}'")
                continue

            seen_urls.add(normalized_url)

            # Match against research sources
            if normalized_url in source_urls:
                matched_title = source_title_map.get(normalized_url)
                results.append(CitationAuditResult(
                    url=raw_url,
                    title=title,
                    status="matched",
                    matched_document_title=matched_title,
                ))
                logger.debug(f"CitationVerifier: matched citation '{raw_url}' -> '{matched_title}'")
            else:
                results.append(CitationAuditResult(
                    url=raw_url,
                    title=title,
                    status="unmatched",
                    matched_document_title=None,
                ))
                logger.debug(f"CitationVerifier: unmatched citation: '{raw_url}'")

        matched_count = sum(1 for r in results if r.status == "matched")
        logger.info(
            f"CitationVerifier: {len(citations_used)} citations evaluated — "
            f"{matched_count} matched, {duplicate_count} duplicates, "
            f"{sum(1 for r in results if r.status == 'unmatched')} unmatched."
        )
        return results, duplicate_count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalizes a URL for comparison by stripping trailing slashes and lowercasing scheme/host.

        Args:
            url: Raw URL string.

        Returns:
            Normalized URL string.
        """
        url = url.strip().rstrip("/")
        # Lowercase scheme and netloc only
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "/" in rest:
                host, path = rest.split("/", 1)
                url = f"{scheme.lower()}://{host.lower()}/{path}"
            else:
                url = f"{scheme.lower()}://{rest.lower()}"
        return url
