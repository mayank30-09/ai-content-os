"""Plugins package for Research Engine."""

from modules.research.plugins.docs_plugin import DocumentationPlugin
from modules.research.plugins.github_plugin import GitHubPlugin
from modules.research.plugins.reddit_plugin import RedditPlugin
from modules.research.plugins.web_plugin import WebPlugin
from modules.research.plugins.youtube_plugin import YouTubePlugin

__all__ = [
    "WebPlugin",
    "GitHubPlugin",
    "RedditPlugin",
    "YouTubePlugin",
    "DocumentationPlugin",
]
