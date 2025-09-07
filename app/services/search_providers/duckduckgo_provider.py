"""
DuckDuckGo search provider implementation
"""
import time
import requests
from typing import List
from app.core.logger import logger
from .base_provider import SearchProvider, SearchResult

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.warning("duckduckgo-search package not available, using API fallback")

class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo search provider (free, no API key required)"""
    
    def __init__(self):
        self.use_ddgs_package = DDGS_AVAILABLE
        self.name = "DuckDuckGo"
        logger.info(f"DuckDuckGo provider initialized (package available: {DDGS_AVAILABLE})")
        
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using DuckDuckGo"""
        
        try:
            if self.use_ddgs_package:
                return self._ddgs_package_search(query, max_results)
            else:
                return self._ddgs_api_search(query, max_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []
    
    def _ddgs_package_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using duckduckgo-search package"""
        
        ddgs = DDGS()
        results = []
        
        search_results = ddgs.text(query, max_results=max_results)
        
        for result in search_results:
            results.append(SearchResult(
                title=result.get('title', ''),
                url=result.get('href', ''),
                snippet=result.get('body', ''),
                source='duckduckgo_package',
                metadata={'provider': 'ddgs_package'}
            ))
        
        logger.info(f"DuckDuckGo package search returned {len(results)} results")
        return results
    
    def _ddgs_api_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using DuckDuckGo Instant Answer API"""
        
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Abstract/instant answer
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("Heading", query),
                url=data.get("AbstractURL", ""),
                snippet=data.get("Abstract", ""),
                source='duckduckgo_api',
                metadata={'type': 'abstract', 'provider': 'ddgs_api'}
            ))
        
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results-len(results)]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(SearchResult(
                    title=topic.get("Text", "")[:100],
                    url=topic.get("FirstURL", ""),
                    snippet=topic.get("Text", ""),
                    source='duckduckgo_api',
                    metadata={'type': 'related_topic', 'provider': 'ddgs_api'}
                ))
        
        # Direct answer
        if not results and data.get("Answer"):
            results.append(SearchResult(
                title=f"Answer: {query}",
                url=data.get("AnswerURL", ""),
                snippet=data.get("Answer", ""),
                source='duckduckgo_api',
                metadata={'type': 'answer', 'provider': 'ddgs_api'}
            ))
        
        logger.info(f"DuckDuckGo API search returned {len(results)} results")
        return results[:max_results]
    
    def is_available(self) -> bool:
        """DuckDuckGo is always available (no API key needed)"""
        return True
    
    def get_provider_info(self) -> dict:
        return {
            'name': self.name,
            'cost': 'free',
            'rate_limits': 'moderate',
            'api_key_required': False,
            'package_available': DDGS_AVAILABLE,
            'capabilities': ['web_search', 'instant_answers', 'related_topics']
        }