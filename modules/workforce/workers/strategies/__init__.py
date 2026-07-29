"""Strategies package init exporting research strategy classes."""

from modules.workforce.workers.strategies.base_strategy import BaseResearchStrategy
from modules.workforce.workers.strategies.community_strategy import CommunityResearchStrategy
from modules.workforce.workers.strategies.general_strategy import GeneralResearchStrategy
from modules.workforce.workers.strategies.media_strategy import MediaResearchStrategy
from modules.workforce.workers.strategies.technical_strategy import TechnicalResearchStrategy

__all__ = [
    "BaseResearchStrategy",
    "GeneralResearchStrategy",
    "TechnicalResearchStrategy",
    "CommunityResearchStrategy",
    "MediaResearchStrategy",
]
