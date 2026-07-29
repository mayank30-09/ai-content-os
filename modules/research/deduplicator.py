"""Deduplicator module for Research Engine.

Identifies and prunes duplicate research documents using URL canonicalization,
normalized title similarity, and content Jaccard similarity.
"""

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from loguru import logger

from modules.research.models import ResearchDocument


class Deduplicator:
    """Detects and prunes duplicate documents across multi-source plugins."""

    def __init__(self, title_threshold: float = 0.85, content_threshold: float = 0.80):
        self.title_threshold: float = title_threshold
        self.content_threshold: float = content_threshold

    def canonicalize_url(self, url: str) -> str:
        """Normalizes URL string by stripping utm tracking parameters and trailing slashes.

        Args:
            url: Input URL string.

        Returns:
            str: Canonicalized URL string.
        """
        if not url:
            return ""
        parsed = urlparse(url.strip())
        # Filter out tracking parameters
        clean_query = [
            (k, v) for k, v in parse_qsl(parsed.query)
            if not k.startswith("utm_") and k not in ("ref", "source")
        ]
        new_query = urlencode(clean_query)
        clean_path = parsed.path.rstrip("/")
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            new_query,
            ""  # Strip fragment
        ))

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculates word Jaccard similarity between two title strings."""
        words1 = set(re.findall(r"\w+", title1.lower()))
        words2 = set(re.findall(r"\w+", title2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculates 3-gram word Jaccard similarity between two content strings."""
        def get_ngrams(text: str, n: int = 3) -> set[str]:
            tokens = re.findall(r"\w+", text.lower())
            if len(tokens) < n:
                return set(tokens)
            return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}

        ngrams1 = get_ngrams(content1)
        ngrams2 = get_ngrams(content2)
        if not ngrams1 or not ngrams2:
            return 0.0
        return len(ngrams1.intersection(ngrams2)) / len(ngrams1.union(ngrams2))

    def deduplicate(self, documents: list[ResearchDocument]) -> list[ResearchDocument]:
        """Prunes duplicate documents from list based on URL, title, and content.

        Args:
            documents: Input list of ResearchDocument objects.

        Returns:
            List[ResearchDocument]: Filtered list containing unique documents.
        """
        unique_docs: list[ResearchDocument] = []
        seen_urls: set[str] = set()

        for doc in documents:
            # 1. Exact canonical URL check
            if doc.url:
                c_url = self.canonicalize_url(doc.url)
                if c_url in seen_urls:
                    logger.debug(f"Pruned duplicate document by URL: '{doc.url}'")
                    continue
                seen_urls.add(c_url)

            # 2. Similarity check against previously accepted documents
            is_dup = False
            for accepted in unique_docs:
                t_sim = self._title_similarity(doc.title, accepted.title)
                if t_sim >= self.title_threshold:
                    logger.debug(f"Pruned duplicate document by title similarity ({t_sim:.2f}): '{doc.title}'")
                    is_dup = True
                    break

                c_sim = self._content_similarity(doc.content, accepted.content)
                if c_sim >= self.content_threshold:
                    logger.debug(f"Pruned duplicate document by content similarity ({c_sim:.2f}): '{doc.title}'")
                    is_dup = True
                    break

            if not is_dup:
                unique_docs.append(doc)

        logger.info(f"Deduplication completed: Reduced {len(documents)} docs to {len(unique_docs)} unique docs.")
        return unique_docs

deduplicator = Deduplicator()
