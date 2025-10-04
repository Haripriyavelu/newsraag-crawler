"""
HTML content extractor - extends IContentExtractor without modifying base code.
"""

from bs4 import BeautifulSoup
import aiohttp
from typing import Optional
from .content_extractor import IContentExtractor


class HTMLContentExtractor(IContentExtractor):
    """Extract content from HTML pages using BeautifulSoup."""
    
    def __init__(self, selectors: str = ".content, .article-body, .post-content, article"):
        """Initialize with CSS selectors for content."""
        self.selectors = [s.strip() for s in selectors.split(',')]
    
    async def extract_content(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Extract content from HTML page."""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.ads']):
                    tag.decompose()
                
                # Try each selector
                for selector in self.selectors:
                    element = soup.select_one(selector)
                    if element:
                        content = element.get_text(separator=' ', strip=True)
                        if len(content) > 100:  # Must have substantial content
                            return content
                
                return None
                
        except Exception:
            return None
    
    def can_handle(self, url: str) -> bool:
        """Can handle any HTTP URL."""
        return url.startswith(('http://', 'https://'))


class KabutanContentExtractor(HTMLContentExtractor):
    """Kabutan-specific content extraction."""
    
    def __init__(self):
        super().__init__(".news-body, .article-body, .news-content")
    
    def can_handle(self, url: str) -> bool:
        return 'kabutan.jp' in url


class PoundSterlingContentExtractor(HTMLContentExtractor):
    """PoundSterlingLive-specific content extraction."""
    
    def __init__(self):
        super().__init__(".entry-content, .post-content, .article-content")
    
    def can_handle(self, url: str) -> bool:
        return 'poundsterlinglive.com' in url
