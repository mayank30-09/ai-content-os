"""Specialized worker stubs package for AI Workforce Core subsystem."""

from modules.workforce.workers.carousel_worker import CarouselWorker
from modules.workforce.workers.copywriter_worker import CopywriterWorker
from modules.workforce.workers.publisher_worker import PublisherWorker
from modules.workforce.workers.research_worker import ResearchWorker
from modules.workforce.workers.script_worker import ScriptWorker

__all__ = [
    "ResearchWorker",
    "ScriptWorker",
    "CarouselWorker",
    "CopywriterWorker",
    "PublisherWorker",
]
