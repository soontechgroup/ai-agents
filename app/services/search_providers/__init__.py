"""
Search providers package for ai-agents
"""
from .base_provider import SearchProvider, SearchResult
from .duckduckgo_provider import DuckDuckGoProvider

__all__ = ['SearchProvider', 'SearchResult', 'DuckDuckGoProvider']