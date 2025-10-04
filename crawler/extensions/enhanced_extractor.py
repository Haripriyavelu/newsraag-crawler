"""
Enhanced content extractor - follows Open-Closed Principle.
Extends base template functionality without modifying core code.
"""

from typing import Optional
import aiohttp
from bs4 import BeautifulSoup

from ..templates.base_template import BaseContentExtractor


class EnhancedContentExtractor(BaseContentExtractor):
    """Enhanced content extractor that adds HTML scraping capability."""
    
    def __init__(self, config):
        super().__init__(config)
        # HTML scraping configuration from YAML
        self.html_selectors = getattr(config, 'selectors', {})
        self.enable_html_extraction = getattr(config, 'content_extraction', '') == 'html'
    
    async def extract_content(self, article_meta, session: aiohttp.ClientSession) -> str:
        """Extract content with HTML fallback capability."""
        
        # First try the original method
        original_content = await super().extract_content(article_meta, session)
        
        # If original extraction worked and we have substantial content, use it
        if original_content and len(original_content.strip()) > 200:
            return original_content
        
        # Otherwise, try HTML extraction if enabled
        if self.enable_html_extraction and article_meta.url:
            html_content = await self._extract_html_content(article_meta.url, session)
            if html_content:
                return html_content
        
        # Fallback to original content
        return original_content or ""
    
    async def _extract_html_content(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Extract content from HTML page using simple selectors."""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Clean unwanted elements
                for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', '.ads']):
                    unwanted.decompose()
                
                # Try configured selectors first
                if self.html_selectors:
                    content_selector = self.html_selectors.get('content', '')
                    if content_selector:
                        element = soup.select_one(content_selector)
                        if element:
                            content = element.get_text(separator=' ', strip=True)
                            if len(content) > 100:
                                return content
                
                # Fallback to common content selectors
                common_selectors = [
                    '.content', '.article-body', '.post-content', '.entry-content',
                    'article', '.main-content', '.story-body'
                ]
                
                for selector in common_selectors:
                    element = soup.select_one(selector)
                    if element:
                        content = element.get_text(separator=' ', strip=True)
                        if len(content) > 100:
                            return content
                
                return None
                
        except Exception:
            return None
