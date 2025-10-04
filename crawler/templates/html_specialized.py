"""
Site-specific HTML scraping implementations.
Optimized selectors and logic for Kabutan and PoundSterlingLive.
"""

from .html_template import HTMLTemplate
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import re


class KabutanTemplate(HTMLTemplate):
    """Specialized template for Kabutan.jp (Japanese stock news)."""
    
    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)
        
        # Kabutan-specific selectors
        self.default_selectors.update({
            'title': [
                '.news-title', 
                '.headline', 
                'h1.title',
                '.article-title',
                'h1'
            ],
            'content': [
                '.news-body',
                '.article-body', 
                '.news-content',
                '.content-body',
                '.article-text',
                'div[class*="content"]'
            ],
            'author': [
                '.author',
                '.byline', 
                '.writer'
            ],
            'date': [
                '.news-date',
                '.published-date',
                '.article-date', 
                'time[datetime]',
                '.date'
            ],
            'links': [
                'a[href*="/news/"]',
                'a[href*="/marketnews/"]', 
                '.news-list a',
                '.article-list a'
            ]
        })

    def _is_article_url(self, url: str) -> bool:
        """Kabutan-specific URL filtering."""
        if not super()._is_article_url(url):
            return False
        
        # Kabutan-specific patterns
        kabutan_patterns = [
            '/news/', '/marketnews/', '/press/', '/company/'
        ]
        
        url_lower = url.lower()
        for pattern in kabutan_patterns:
            if pattern in url_lower:
                return True
        
        # Skip non-news URLs
        skip_patterns = [
            '/chart/', '/company_list/', '/search', 
            '/ranking/', '/tools/', '/help/'
        ]
        
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
                
        return True

    def _clean_soup(self, soup: BeautifulSoup):
        """Kabutan-specific content cleaning."""
        super()._clean_soup(soup)
        
        # Remove Kabutan-specific unwanted elements
        kabutan_unwanted = [
            '.advertising',
            '.banner',
            '.stock-chart',
            '.related-stock',
            '.company-info-box',
            '.sidebar',
            '.navigation'
        ]
        
        for selector in kabutan_unwanted:
            for element in soup.select(selector):
                element.decompose()


class PoundSterlingLiveTemplate(HTMLTemplate):
    """Specialized template for PoundSterlingLive.com (forex news)."""
    
    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)
        
        # PoundSterlingLive-specific selectors  
        self.default_selectors.update({
            'title': [
                '.entry-title',
                '.post-title',
                '.article-title', 
                'h1.title',
                'h1'
            ],
            'content': [
                '.entry-content',
                '.post-content',
                '.article-content',
                '.content-area',
                'div[class*="content"]',
                '.story-body'
            ],
            'author': [
                '.author-name',
                '.byline',
                '.post-author',
                '.author'
            ],
            'date': [
                '.entry-date',
                '.post-date',
                '.published-date',
                'time[datetime]',
                '.date'
            ],
            'links': [
                'a[href*="/news/"]',
                'a[href*="/analysis/"]',
                'a[href*="/markets/"]',
                '.post-title a',
                '.entry-title a',
                'h2 a, h3 a'
            ]
        })

    def _is_article_url(self, url: str) -> bool:
        """PoundSterlingLive-specific URL filtering."""
        if not super()._is_article_url(url):
            return False
            
        # PoundSterlingLive-specific patterns
        psl_patterns = [
            '/news/', '/analysis/', '/markets/', '/economics/',
            '/forex/', '/gbp/', '/eur/', '/usd/'
        ]
        
        url_lower = url.lower()
        for pattern in psl_patterns:
            if pattern in url_lower:
                return True
        
        # Skip non-article URLs
        skip_patterns = [
            '/category/', '/tag/', '/author/', '/page/',
            '/rates/', '/calculator/', '/tools/'
        ]
        
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
                
        return True

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Enhanced content extraction for PoundSterlingLive."""
        content = super()._extract_content(soup)
        
        # PoundSterlingLive often has summary paragraphs - include them
        summary_selectors = ['.excerpt', '.summary', '.lead', '.intro']
        
        for selector in summary_selectors:
            element = soup.select_one(selector)
            if element:
                summary = element.get_text(strip=True)
                if summary and summary not in content:
                    content = summary + '\n\n' + content
                    break
        
        return content

    def _clean_soup(self, soup: BeautifulSoup):
        """PoundSterlingLive-specific content cleaning."""
        super()._clean_soup(soup)
        
        # Remove PoundSterlingLive-specific unwanted elements
        psl_unwanted = [
            '.social-sharing',
            '.newsletter-signup', 
            '.rate-table',
            '.currency-converter',
            '.related-articles',
            '.author-bio',
            '.comments-section'
        ]
        
        for selector in psl_unwanted:
            for element in soup.select(selector):
                element.decompose()


def create_html_template(source_name: str, config: Dict[str, Any]) -> HTMLTemplate:
    """Factory function to create appropriate HTML template based on source."""
    
    if 'kabutan' in source_name.lower():
        return KabutanTemplate(source_name, config)
    elif 'poundsterling' in source_name.lower() or 'psl' in source_name.lower():
        return PoundSterlingLiveTemplate(source_name, config)
    else:
        # Generic HTML template for other sources
        return HTMLTemplate(source_name, config)
