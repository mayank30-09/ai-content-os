"""Specialized worker stubs package for AI Workforce Core subsystem."""

from modules.workforce.workers.carousel_worker import CarouselWorker
from modules.workforce.workers.copywriter_worker import CopywriterWorker
from modules.workforce.workers.memory_worker import MemoryWorker
from modules.workforce.workers.publisher_worker import PublisherWorker
from modules.workforce.workers.research_worker import ResearchWorker
from modules.workforce.workers.script_worker import ScriptWorker
from modules.workforce.workers.strategist_worker import ContentStrategistWorker
from modules.workforce.workers.writer_worker import WriterWorker

__all__ = [
    "ResearchWorker",
    "MemoryWorker",
    "ContentStrategistWorker",
    "WriterWorker",
    "ScriptWorker",
    "CarouselWorker",
    "CopywriterWorker",
    "PublisherWorker",
]
