"""
Web Search Service for AI-Agents
Production-ready search wrapper with DuckDuckGo integration
"""
import os
from typing import List, Dict, Any
from app.core.logger import logger
from app.core.config import settings
from app.services.search_providers import DuckDuckGoProvider, SearchResult

class WebSearchService:
    """Main web search service for production use"""
    
    def __init__(self):
        # Initialize DuckDuckGo provider
        self.provider = DuckDuckGoProvider()
        
        # Get search provider preference from config
        self.search_provider = getattr(settings, 'SEARCH_PROVIDER', os.getenv('SEARCH_PROVIDER', 'duckduckgo'))
        
        logger.info(f"WebSearchService initialized with provider: {self.search_provider}")
        
        if not self.provider.is_available():
            logger.error("No search providers available")
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Execute search and return results as dictionaries"""
        
        if not self.provider.is_available():
            logger.warning("Search provider not available")
            return []
        
        try:
            # Get SearchResult objects from provider
            search_results = self.provider.search(query, max_results)
            
            # Convert to dictionary format for API compatibility
            dict_results = []
            for result in search_results:
                dict_results.append({
                    'title': result.title,
                    'url': result.url,
                    'snippet': result.snippet,
                    'source': result.source,
                    'timestamp': result.timestamp,
                    'metadata': result.metadata
                })
            
            logger.info(f"Search completed: {len(dict_results)} results for query '{query[:50]}...'")
            return dict_results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    def is_search_needed(self, query: str) -> bool:
        """Determine if a query requires web search based on keywords"""
        
        query_lower = query.lower()
        
        search_indicators = [
            'latest', 'recent', 'current', 'news', 'today', 'now', 'this year',
            'what happened', 'search for', 'find information', 'look up',
            'update on', 'status of', 'trending', 'new', 'developments',
            '2024', '2025', 'currently', 'nowadays', 'breaking', 'real-time'
        ]
        
        has_search_indicator = any(indicator in query_lower for indicator in search_indicators)
        
        if has_search_indicator:
            logger.debug(f"Query '{query[:50]}...' identified as needing web search")
        
        return has_search_indicator
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the search service"""
        
        provider_info = self.provider.get_provider_info()
        
        return {
            'service_name': 'WebSearchService',
            'version': '1.0.0',
            'provider': provider_info,
            'configuration': {
                'search_provider': self.search_provider,
                'provider_available': self.provider.is_available()
            },
            'capabilities': [
                'Web search',
                'Query analysis',
                'Search need detection'
            ]
        }
    
    def test_search(self) -> Dict[str, Any]:
        """Test the search functionality"""
        
        test_query = "artificial intelligence 2025"
        
        try:
            results = self.search(test_query, max_results=2)
            
            return {
                'test_successful': len(results) > 0,
                'query': test_query,
                'results_count': len(results),
                'provider_available': self.provider.is_available(),
                'provider_info': self.provider.get_provider_info()
            }
            
        except Exception as e:
            logger.error(f"Search test failed: {e}")
            return {
                'test_successful': False,
                'error': str(e),
                'provider_available': self.provider.is_available()
            }