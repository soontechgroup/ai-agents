"""
Base classes for search providers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time

@dataclass
class SearchResult:
    """Standardized search result format"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: float = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
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