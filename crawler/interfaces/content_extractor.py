"""
Content extractor interface following Open-Closed Principle.
Allows extending content extraction without modifying base template.
"""

from abc import ABC, abstractmethod
from typing import Optional
import aiohttp


class IContentExtractor(ABC):
    """Interface for content extraction strategies."""
    
    @abstractmethod
    async def extract_content(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Extract content from URL."""
        pass
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        pass


class DefaultContentExtractor(IContentExtractor):
    """Default content extraction - just returns empty for non-RSS."""
    
    async def extract_content(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        return None
    
    def can_handle(self, url: str) -> bool:
        return True  # Fallback handler
