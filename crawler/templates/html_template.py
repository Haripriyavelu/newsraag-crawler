"""
HTML scraping template for news sources that require web scraping.
Handles sites like Kabutan and PoundSterlingLive using BeautifulSoup.
"""

import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import re
import logging
from dateutil import parser as date_parser

from .base_template import BaseNewsSourceTemplate
from ..interfaces import ArticleMetadata, SourceType, ContentType
from ..utils.rate_limiter import RateLimiter


class HTMLTemplate(BaseNewsSourceTemplate):
    """Template for HTML scraping-based news sources."""
    
    def __init__(self, source_name: str, config: Dict[str, Any]):
        """Initialize HTML scraping template."""
        super().__init__(source_name, config)
        
        self.base_url = config.get('url', '')
        self.selectors = config.get('selectors', {})
        self.requires_translation = config.get('translate', False)
        self.rate_limiter = RateLimiter(config.get('rate_limit', 2))
        
        # Default selectors for common article elements
        self.default_selectors = {
            'title': ['h1', '.title', '.headline', '.article-title', '.entry-title'],
            'content': ['.article-body', '.content', '.post-content', '.entry-content', 
                       '.article-text', '.story-body', 'article', '.main-content'],
            'author': ['.author', '.by-author', '.byline', '.writer', '.author-name'],
            'date': ['.date', '.published', '.timestamp', '.post-date', 'time[datetime]'],
            'links': ['a[href]']  # For finding article links
        }
        
        # Merge with configured selectors
        for key, value in self.selectors.items():
            if isinstance(value, str):
                self.default_selectors[key] = [value]
            elif isinstance(value, list):
                self.default_selectors[key] = value

    async def fetch_articles(self, session: aiohttp.ClientSession, 
                           max_articles: Optional[int] = None) -> List[ArticleMetadata]:
        """Fetch articles by scraping HTML content."""
        articles = []
        
        try:
            # Step 1: Get main page to find article links
            article_links = await self._discover_article_links(session)
            
            if not article_links:
                print(f"No article links found for {self.source_name}")
                return articles
            
            # Step 2: Limit articles if specified
            if max_articles:
                article_links = article_links[:max_articles]
            
            print(f"Found {len(article_links)} article links for {self.source_name}")
            
            # Step 3: Process each article
            for i, link_info in enumerate(article_links, 1):
                try:
                    # Apply rate limiting
                    await self.rate_limiter.wait()
                    
                    article = await self._extract_article_content(session, link_info)
                    if article:
                        articles.append(article)
                        print(f"Processed article {i}/{len(article_links)}: {article.title[:50]}...")
                    else:
                        print(f"Failed to extract article {i}/{len(article_links)}: {link_info.get('url', 'Unknown URL')}")
                        
                except Exception as e:
                    print(f"Error processing article {i}/{len(article_links)}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching articles from {self.source_name}: {str(e)}")
            
        return articles

    async def _discover_article_links(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Discover article links from the main page."""
        try:
            print(f"Discovering article links from: {self.base_url}")
            
            async with session.get(self.base_url, timeout=30) as response:
                if response.status != 200:
                    print(f"Failed to fetch main page: HTTP {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                self._clean_soup(soup)
                
                article_links = []
                
                # Strategy 1: Look for article-specific link patterns
                link_selectors = [
                    'a[href*="/news/"]',     # Common news URL pattern
                    'a[href*="/article/"]',  # Common article URL pattern
                    'a[href*="/post/"]',     # Blog post pattern
                    '.article-link a',       # Article wrapper links
                    '.news-item a',          # News item links
                    '.headline a',           # Headline links
                    '.title a',              # Title links
                    'h1 a, h2 a, h3 a',     # Header links
                ]
                
                found_links = set()  # Prevent duplicates
                
                for selector in link_selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href', '')
                        if href and href not in found_links:
                            # Convert relative URLs to absolute
                            full_url = urljoin(self.base_url, href)
                            
                            # Basic filtering for article-like URLs
                            if self._is_article_url(full_url):
                                found_links.add(href)
                                
                                # Extract preview information
                                title = self._extract_link_title(link)
                                date_str = self._extract_link_date(link)
                                
                                article_links.append({
                                    'url': full_url,
                                    'title': title,
                                    'date_str': date_str,
                                    'source_element': str(link)[:200] + '...' if len(str(link)) > 200 else str(link)
                                })
                
                print(f"Discovered {len(article_links)} unique article links")
                
                # Sort by date if available (newest first)
                article_links = self._sort_articles_by_date(article_links)
                
                return article_links
                
        except Exception as e:
            print(f"Error discovering article links: {str(e)}")
            return []

    async def _extract_article_content(self, session: aiohttp.ClientSession, 
                                     link_info: Dict[str, Any]) -> Optional[ArticleMetadata]:
        """Extract full content from an individual article page."""
        url = link_info['url']
        
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    print(f"Failed to fetch article: HTTP {response.status} for {url}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                self._clean_soup(soup)
                
                # Extract article components
                title = self._extract_title(soup, link_info.get('title', ''))
                content = self._extract_content(soup)
                author = self._extract_author(soup)
                published_date = self._extract_date(soup, link_info.get('date_str', ''))
                
                if not title or not content:
                    print(f"Missing essential content - Title: {bool(title)}, Content: {bool(content)}")
                    return None
                
                if len(content.strip()) < 100:  # Too short to be meaningful
                    print(f"Content too short: {len(content)} characters")
                    return None
                
                # Create metadata
                article_id = self._generate_article_id(url, title)
                
                return ArticleMetadata(
                    title=title.strip(),
                    url=url,
                    content=content.strip(),
                    author=author.strip() if author else None,
                    published_date=published_date,
                    source_name=self.source_name,
                    article_id=article_id,
                    category=self._extract_category(soup),
                    tags=self._extract_tags(soup)
                )
                
        except Exception as e:
            print(f"Error extracting article content from {url}: {str(e)}")
            return None

    def _clean_soup(self, soup: BeautifulSoup):
        """Remove unwanted elements from soup."""
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove common unwanted elements
        unwanted_selectors = [
            'script', 'style', 'nav', 'header', 'footer', 
            '.advertisement', '.ads', '.sidebar', '.related-posts',
            '.comments', '.social-share', '.newsletter-signup',
            '.cookie-banner', '.popup', '.modal'
        ]
        
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

    def _extract_title(self, soup: BeautifulSoup, fallback_title: str = '') -> str:
        """Extract article title using multiple strategies."""
        for selector in self.default_selectors['title']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        # Fallback to meta tags
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            return meta_title.get('content', '')
        
        # Fallback to page title
        page_title = soup.find('title')
        if page_title:
            title = page_title.get_text(strip=True)
            # Remove common site name suffixes
            title = re.sub(r'\s*[-|]\s*[^-|]*$', '', title)
            return title
        
        return fallback_title

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content."""
        content_parts = []
        
        for selector in self.default_selectors['content']:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(separator=' ', strip=True)
                if text and len(text) > 50:  # Only substantial content
                    content_parts.append(text)
        
        # Combine and clean content
        full_content = ' '.join(content_parts)
        
        # Clean up whitespace
        full_content = re.sub(r'\s+', ' ', full_content)
        
        return full_content.strip()

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article author."""
        for selector in self.default_selectors['author']:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Try meta tags
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author:
            return meta_author.get('content', '')
        
        return None

    def _extract_date(self, soup: BeautifulSoup, fallback_date: str = '') -> Optional[datetime]:
        """Extract article publication date."""
        # Try structured data first
        for selector in self.default_selectors['date']:
            element = soup.select_one(selector)
            if element:
                # Check for datetime attribute
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    try:
                        return date_parser.parse(datetime_attr)
                    except:
                        pass
                
                # Try text content
                date_text = element.get_text(strip=True)
                if date_text:
                    try:
                        return date_parser.parse(date_text)
                    except:
                        pass
        
        # Try meta tags
        meta_selectors = [
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'date'}),
            ('meta', {'name': 'pubdate'}),
            ('meta', {'name': 'publish_date'})
        ]
        
        for tag, attrs in meta_selectors:
            meta = soup.find(tag, attrs)
            if meta:
                content = meta.get('content', '')
                if content:
                    try:
                        return date_parser.parse(content)
                    except:
                        pass
        
        # Try fallback date
        if fallback_date:
            try:
                return date_parser.parse(fallback_date)
            except:
                pass
        
        # Default to current time
        return datetime.now(timezone.utc)

    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article category."""
        category_selectors = [
            '.category', '.post-category', '.article-category',
            '[data-category]', '.breadcrumb a:last-child'
        ]
        
        for selector in category_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract article tags."""
        tags = []
        
        tag_selectors = [
            '.tags a', '.tag', '.post-tag', '.article-tag'
        ]
        
        for selector in tag_selectors:
            elements = soup.select(selector)
            for element in elements:
                tag = element.get_text(strip=True)
                if tag and tag not in tags:
                    tags.append(tag)
        
        return tags

    def _is_article_url(self, url: str) -> bool:
        """Determine if URL likely points to an article."""
        # Skip non-HTTP URLs
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Skip common non-article patterns
        skip_patterns = [
            '/search', '/category', '/tag', '/author', '/page/',
            '/login', '/register', '/contact', '/about',
            '.pdf', '.jpg', '.png', '.gif', '.css', '.js',
            '/api/', '/rss', '/feed', '/sitemap'
        ]
        
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Look for positive article patterns
        article_patterns = [
            '/news/', '/article/', '/post/', '/story/',
            '/blog/', '/press-release/', '/analysis/'
        ]
        
        for pattern in article_patterns:
            if pattern in url_lower:
                return True
        
        # Check if URL has date-like patterns (common in news URLs)
        if re.search(r'/20\d{2}/', url) or re.search(r'/\d{4}-\d{2}-\d{2}/', url):
            return True
        
        return True  # Default to including the URL

    def _extract_link_title(self, link_element) -> str:
        """Extract title from link element."""
        # Try title attribute
        title = link_element.get('title', '').strip()
        if title:
            return title
        
        # Try link text
        text = link_element.get_text(strip=True)
        if text:
            return text
        
        # Try alt text from images
        img = link_element.find('img')
        if img:
            alt = img.get('alt', '').strip()
            if alt:
                return alt
        
        return ''

    def _extract_link_date(self, link_element) -> str:
        """Extract date from link element or parent."""
        # Look in parent elements for date information
        current = link_element
        for _ in range(3):  # Check up to 3 parent levels
            if current:
                # Look for date-related attributes or classes
                for attr in ['data-date', 'data-published', 'datetime']:
                    date_value = current.get(attr)
                    if date_value:
                        return date_value
                
                # Look for date-like text in siblings
                parent = current.parent
                if parent:
                    date_text = parent.get_text()
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', date_text)
                    if date_match:
                        return date_match.group()
                
                current = current.parent
            else:
                break
        
        return ''

    def _sort_articles_by_date(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort articles by date, newest first."""
        def date_key(article):
            date_str = article.get('date_str', '')
            if date_str:
                try:
                    return date_parser.parse(date_str)
                except:
                    pass
            return datetime.min
        
        return sorted(articles, key=date_key, reverse=True)

    def _generate_article_id(self, url: str, title: str) -> str:
        """Generate unique article ID."""
        import hashlib
        content_for_id = f"{url}_{title}_{self.source_name}"
        return hashlib.md5(content_for_id.encode('utf-8')).hexdigest()
