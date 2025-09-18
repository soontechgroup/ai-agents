"""
Flexible Web Search Service with Multiple Provider Support
Test version for ai-chatbot-demo before integration into ai-agents
"""
import time
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import os

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("[SEARCH] duckduckgo-search package not available")

@dataclass
class SearchResult:
    """Standardized search result format"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class SearchProvider(ABC):
    """Abstract base class for search providers"""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute search and return standardized results"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available/configured"""
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about this provider"""
        pass

class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo search provider (free, no API key)"""
    
    def __init__(self):
        self.use_ddgs_package = DDGS_AVAILABLE
        self.name = "DuckDuckGo"
        
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using DuckDuckGo"""
        
        try:
            if self.use_ddgs_package:
                return self._ddgs_package_search(query, max_results)
            else:
                return self._ddgs_api_search(query, max_results)
        except Exception as e:
            print(f"[SEARCH] DuckDuckGo search failed: {e}")
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
                timestamp=time.time(),
                metadata={'provider': 'ddgs_package'}
            ))
        
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
                timestamp=time.time(),
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
                    timestamp=time.time(),
                    metadata={'type': 'related_topic', 'provider': 'ddgs_api'}
                ))
        
        # Direct answer
        if not results and data.get("Answer"):
            results.append(SearchResult(
                title=f"Answer: {query}",
                url=data.get("AnswerURL", ""),
                snippet=data.get("Answer", ""),
                source='duckduckgo_api',
                timestamp=time.time(),
                metadata={'type': 'answer', 'provider': 'ddgs_api'}
            ))
        
        return results[:max_results]
    
    def is_available(self) -> bool:
        """DuckDuckGo is always available (no API key needed)"""
        return True
    
    def get_provider_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'cost': 'free',
            'rate_limits': 'moderate',
            'api_key_required': False,
            'package_available': DDGS_AVAILABLE,
            'capabilities': ['web_search', 'instant_answers', 'related_topics']
        }

class SerperProvider(SearchProvider):
    """Serper.dev search provider (requires API key)"""
    
    def __init__(self):
        self.api_key = os.getenv('SERPER_API_KEY')
        self.name = "Serper"
        
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using Serper API"""
        
        if not self.api_key:
            print("[SEARCH] Serper API key not configured")
            return []
        
        url = "https://google.serper.dev/search"
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'q': query,
            'num': max_results
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Process organic results
            for item in data.get('organic', [])[:max_results]:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    source='serper',
                    timestamp=time.time(),
                    metadata={
                        'provider': 'serper',
                        'position': item.get('position', 0),
                        'date': item.get('date')
                    }
                ))
            
            # Add knowledge graph if available
            if data.get('knowledgeGraph') and len(results) < max_results:
                kg = data['knowledgeGraph']
                results.append(SearchResult(
                    title=kg.get('title', query),
                    url=kg.get('website', ''),
                    snippet=kg.get('description', ''),
                    source='serper',
                    timestamp=time.time(),
                    metadata={'provider': 'serper', 'type': 'knowledge_graph'}
                ))
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"[SEARCH] Serper API request failed: {e}")
            return []
        except Exception as e:
            print(f"[SEARCH] Serper search failed: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if Serper API key is configured"""
        return bool(self.api_key)
    
    def get_provider_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'cost': 'freemium',
            'rate_limits': '2500 free searches/month',
            'api_key_required': True,
            'api_key_configured': self.is_available(),
            'capabilities': ['web_search', 'knowledge_graph', 'news_search']
        }

class MockProvider(SearchProvider):
    """Mock search provider for testing/fallback"""
    
    def __init__(self):
        self.name = "Mock"
    
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Generate mock search results"""
        
        query_lower = query.lower()
        results = []
        
        # Context-aware mock results
        if 'ai' in query_lower or 'artificial intelligence' in query_lower:
            mock_data = [
                ("Latest AI Developments 2025", "Recent breakthroughs in artificial intelligence including large language models and computer vision."),
                ("AI Applications Across Industries", "AI is transforming healthcare, finance, transportation, and education with innovative solutions."),
                ("Understanding Machine Learning", "Machine learning fundamentals, algorithms, and practical applications for professionals.")
            ]
        elif 'python' in query_lower:
            mock_data = [
                ("Python Programming Best Practices", "Essential Python programming practices, code organization, and performance optimization."),
                ("Python for Data Science", "Popular Python libraries including NumPy, Pandas, and Scikit-learn for data analysis.")
            ]
        else:
            mock_data = [
                (f"Information about {query}", f"Comprehensive information about {query}, including background and context."),
                (f"{query} - Complete Guide", f"A detailed guide covering all aspects of {query} with practical examples.")
            ]
        
        for i, (title, snippet) in enumerate(mock_data[:max_results]):
            results.append(SearchResult(
                title=title,
                url=f"https://example.com/{query.replace(' ', '-').lower()}-{i+1}",
                snippet=snippet,
                source='mock',
                timestamp=time.time(),
                metadata={'provider': 'mock', 'position': i+1}
            ))
        
        return results
    
    def is_available(self) -> bool:
        """Mock provider is always available"""
        return True
    
    def get_provider_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'cost': 'free',
            'rate_limits': 'none',
            'api_key_required': False,
            'capabilities': ['mock_data', 'testing', 'fallback']
        }

class WebSearchTool:
    """Main web search service with provider switching capability"""
    
    def __init__(self):
        # Initialize all providers
        self.providers = {
            'duckduckgo': DuckDuckGoProvider(),
            'serper': SerperProvider(),
            'mock': MockProvider()
        }
        
        # Set default provider order (preference)
        self.provider_order = self._determine_provider_order()
        
        print(f"[SEARCH] WebSearchTool initialized with providers: {list(self.providers.keys())}")
        print(f"[SEARCH] Provider preference order: {self.provider_order}")
        
        # Legacy compatibility
        self.use_mock_data = not any(self.providers[p].is_available() and p != 'mock' for p in self.provider_order)
    
    def _determine_provider_order(self) -> List[str]:
        """Determine provider order based on availability and configuration"""
        
        # Get preferred provider from environment
        preferred_provider = os.getenv('SEARCH_PROVIDER', 'auto')
        
        if preferred_provider != 'auto':
            if preferred_provider in self.providers and self.providers[preferred_provider].is_available():
                return [preferred_provider] + [p for p in self.providers.keys() if p != preferred_provider]
        
        # Auto-determine best order
        order = []
        
        # Prefer providers with API keys if available
        if self.providers['serper'].is_available():
            order.append('serper')
        
        # Always include DuckDuckGo as it's free
        if self.providers['duckduckgo'].is_available():
            order.append('duckduckgo')
        
        # Mock as fallback
        order.append('mock')
        
        return order
    
    def search(self, query: str, max_results: int = 5, provider: str = None) -> List[Dict[str, Any]]:
        """Search using specified provider or auto-fallback (legacy compatible format)"""
        
        # Get SearchResult objects
        search_results = self._search_internal(query, max_results, provider)
        
        # Convert to legacy dict format for compatibility
        legacy_results = []
        for result in search_results:
            legacy_results.append({
                'title': result.title,
                'url': result.url,
                'snippet': result.snippet,
                'source': result.source,
                'timestamp': result.timestamp
            })
        
        return legacy_results
    
    def _search_internal(self, query: str, max_results: int = 5, provider: str = None) -> List[SearchResult]:
        """Internal search method returning SearchResult objects"""
        
        # Use specific provider if requested
        if provider and provider in self.providers:
            if self.providers[provider].is_available():
                try:
                    results = self.providers[provider].search(query, max_results)
                    if results:
                        print(f"[SEARCH] Search completed using {provider}: {len(results)} results")
                        return results
                except Exception as e:
                    print(f"[SEARCH] Search with {provider} failed: {e}")
            else:
                print(f"[SEARCH] Provider {provider} not available")
        
        # Auto-fallback through provider order
        for provider_name in self.provider_order:
            if not self.providers[provider_name].is_available():
                continue
                
            try:
                results = self.providers[provider_name].search(query, max_results)
                if results:
                    print(f"[SEARCH] Search completed using {provider_name}: {len(results)} results")
                    return results
            except Exception as e:
                print(f"[SEARCH] Search with {provider_name} failed: {e}, trying next provider")
                continue
        
        print("[SEARCH] All search providers failed")
        return []
    
    def is_search_needed(self, query: str) -> bool:
        """Determine if a query needs web search"""
        
        query_lower = query.lower()
        
        search_indicators = [
            'latest', 'recent', 'current', 'news', 'today', 'now', 'this year',
            'what happened', 'search for', 'find information', 'look up',
            'update on', 'status of', 'trending', 'new', 'developments',
            '2024', '2025', 'currently', 'nowadays', 'breaking'
        ]
        
        return any(indicator in query_lower for indicator in search_indicators)
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search tool statistics (legacy compatible)"""
        
        available_providers = [name for name, provider in self.providers.items() if provider.is_available()]
        primary_provider = self.provider_order[0] if self.provider_order else 'none'
        
        return {
            'provider': primary_provider,
            'available_providers': available_providers,
            'provider_stats': {name: provider.get_provider_info() for name, provider in self.providers.items()},
            'has_api_key': any(provider.get_provider_info().get('api_key_configured', False) for provider in self.providers.values()),
            'capabilities': [
                'Multi-provider support',
                'Auto-fallback',
                'Rate limit handling',
                'Provider switching'
            ]
        }
    
    def test_providers(self) -> Dict[str, bool]:
        """Test all providers with a simple query"""
        test_query = "test search"
        results = {}
        
        print("[SEARCH] Testing all providers...")
        
        for name, provider in self.providers.items():
            if not provider.is_available():
                results[name] = False
                print(f"[SEARCH] Provider {name}: Not available")
                continue
                
            try:
                search_results = provider.search(test_query, max_results=1)
                results[name] = len(search_results) > 0
                print(f"[SEARCH] Provider {name}: {'✓ Working' if results[name] else '✗ No results'}")
            except Exception as e:
                print(f"[SEARCH] Provider {name}: ✗ Failed ({e})")
                results[name] = False
        
        return results
    
    def set_preferred_provider(self, provider_name: str) -> bool:
        """Set preferred provider for future searches"""
        if provider_name in self.providers and self.providers[provider_name].is_available():
            # Move preferred provider to front of order
            self.provider_order = [provider_name] + [p for p in self.provider_order if p != provider_name]
            print(f"[SEARCH] Preferred provider set to: {provider_name}")
            return True
        return False