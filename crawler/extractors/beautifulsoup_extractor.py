"""
BeautifulSoup extractor for traditional HTML websites.

Uses BeautifulSoup for parsing HTML content from websites that don't require JavaScript.
"""

import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
from loguru import logger
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from crawler.interfaces import ArticleMetadata, SourceConfig
from datetime import datetime
import hashlib
import re


class BeautifulSoupExtractor:
    """Content extractor using BeautifulSoup for HTML parsing."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.session = None
        
        # Default selectors that work for most news sites
        self.selectors = {
            'title': ['h1', '.title', '.headline', '.article-title', '.entry-title', 'title'],
            'content': ['.article-body', '.content', '.post-content', '.entry-content', 
                       '.article-text', '.story-body', 'article', '.main-content', 'main'],
            'date': ['.date', '.published', '.timestamp', '.post-date', 'time[datetime]'],
            'author': ['.author', '.by-author', '.byline', '.writer', '.author-name'],
            'article_links': ['a[href*="/article/"]', 'a[href*="/news/"]', 'a[href*="/post/"]']
        }
        
        # Merge with custom selectors if provided
        if hasattr(config, 'selectors') and config.selectors:
            for key, value in config.selectors.items():
                if isinstance(value, str):
                    self.selectors[key] = [value]
                elif isinstance(value, list):
                    self.selectors[key] = value
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'NewsRagnarok-Crawler/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_website(self, base_url: str, max_articles: int) -> List[ArticleMetadata]:
        """Scrape website to discover and extract articles."""
        articles = []
        
        async with self:
            try:
                logger.info(f"🕷️ Scraping {base_url} with BeautifulSoup")
                
                # First, get the main page
                main_article = await self.extract_article_content(base_url)
                if main_article:
                    articles.append(main_article)
                
                # Then discover article links
                article_links = await self._discover_article_links(base_url)
                
                # Extract content from discovered links
                for url in article_links[:max_articles-1]:  # -1 for main page
                    try:
                        article = await self.extract_article_content(url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to extract {url}: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"BeautifulSoup scraping error: {str(e)}")
                raise
        
        logger.info(f"✅ BeautifulSoup extracted {len(articles)} articles from {base_url}")
        return articles
    
    async def extract_article_content(self, url: str) -> Optional[ArticleMetadata]:
        """Extract content from a specific article URL."""
        try:
            if not self.session:
                async with self:
                    return await self._extract_single_article(url)
            else:
                return await self._extract_single_article(url)
                
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {str(e)}")
            return None
    
    async def _extract_single_article(self, url: str) -> Optional[ArticleMetadata]:
        """Internal method to extract a single article."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove unwanted elements
                for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    unwanted.decompose()
                
                # Extract title
                title = self._extract_with_selectors(soup, self.selectors['title'])
                if not title:
                    title = f"Article from {url}"
                
                # Extract main content  
                content = self._extract_with_selectors(soup, self.selectors['content'])
                if not content or len(content.strip()) < 100:
                    logger.warning(f"Content too short from {url}: {len(content) if content else 0} chars")
                    return None
                
                # Extract metadata
                date_str = self._extract_with_selectors(soup, self.selectors['date'])
                date = datetime.now()
                if date_str:
                    try:
                        # Try to parse the date string
                        from dateutil import parser as date_parser
                        date = date_parser.parse(date_str)
                    except:
                        date = datetime.now()
                
                author = self._extract_with_selectors(soup, self.selectors['author'])
                
                # Generate article ID
                article_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()
                
                return ArticleMetadata(
                    title=title,
                    url=url,
                    published_date=date,
                    source_name=self.config.name,
                    article_id=article_id,
                    author=author or None
                )
                
        except Exception as e:
            logger.error(f"Error in _extract_single_article for {url}: {str(e)}")
            return None
    
    def _extract_with_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract text using a list of CSS selectors."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 10:  # Avoid empty or very short text
                        return text
            except Exception:
                continue
        return ""
    
    async def _discover_article_links(self, base_url: str) -> List[str]:
        """Discover article links from the main page."""
        article_links = []
        
        try:
            async with self.session.get(base_url) as response:
                if response.status != 200:
                    return []
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all links that might be articles
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    
                    # Convert relative URLs to absolute
                    full_url = urljoin(base_url, href)
                    
                    # Filter article-like URLs
                    if self._is_article_url(full_url, base_url):
                        article_links.append(full_url)
                        
        except Exception as e:
            logger.error(f"Error discovering article links from {base_url}: {str(e)}")
        
        # Remove duplicates and limit
        return list(dict.fromkeys(article_links))[:20]
    
    def _is_article_url(self, url: str, base_url: str) -> bool:
        """Check if URL looks like an article URL."""
        # Must be from same domain
        if not url.startswith(base_url.rstrip('/')):
            return False
        
        # Common article URL patterns
        article_patterns = [
            r'/article/',
            r'/news/',
            r'/post/',
            r'/blog/',
            r'/story/',
            r'/analysis/',
            r'/market/',
            r'/forex/',
            r'/stock/',
            r'/trading/',
            r'/\d{4}/\d{2}/',  # Date patterns like /2023/10/
            r'-\d+\.html?$',   # Ending with number.html
        ]
        
        url_lower = url.lower()
        return any(re.search(pattern, url_lower) for pattern in article_patterns)
    
    async def health_check(self) -> bool:
        """Check if BeautifulSoup extractor is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://httpbin.org/html') as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"BeautifulSoup health check failed: {str(e)}")
            return False