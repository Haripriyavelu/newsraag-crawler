"""
Robust RSS parser with enhanced error handling and fallback mechanisms.

This module provides improved RSS parsing with better error recovery
and support for malformed RSS feeds.
"""

import asyncio
import aiohttp
import feedparser
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
from datetime import datetime
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import hashlib


class RobustRSSParser:
    """
    Enhanced RSS parser with robust error handling.
    
    Features:
    - Handles malformed RSS feeds
    - Multiple parsing strategies
    - Fallback mechanisms for broken XML
    - Enhanced error reporting
    """
    
    def __init__(self, timeout: int = 30):
        """Initialize the robust RSS parser."""
        self.timeout = timeout
        self.user_agent = "NewsRagnarok-Crawler/1.0 (+https://newsragnarok.com/bot)"
    
    async def parse_rss_feed(self, rss_url: str, max_articles: int = 50) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse RSS feed with multiple fallback strategies.
        
        Args:
            rss_url: RSS feed URL
            max_articles: Maximum articles to extract
            
        Returns:
            Tuple of (articles_list, error_messages)
        """
        articles = []
        errors = []
        
        logger.info(f"📡 Parsing RSS feed: {rss_url}")
        
        try:
            # Strategy 1: Try standard feedparser
            articles, parse_errors = await self._try_feedparser(rss_url, max_articles)
            errors.extend(parse_errors)
            
            if articles:
                logger.info(f"✅ Successfully parsed {len(articles)} articles using feedparser")
                return articles, errors
            
            # Strategy 2: Try manual XML parsing
            logger.warning("📡 Feedparser failed, trying manual XML parsing...")
            articles, xml_errors = await self._try_manual_xml_parsing(rss_url, max_articles)
            errors.extend(xml_errors)
            
            if articles:
                logger.info(f"✅ Successfully parsed {len(articles)} articles using manual XML parsing")
                return articles, errors
            
            # Strategy 3: Try HTML fallback (look for RSS links)
            logger.warning("📡 XML parsing failed, trying HTML fallback...")
            articles, html_errors = await self._try_html_fallback(rss_url, max_articles)
            errors.extend(html_errors)
            
            if articles:
                logger.info(f"✅ Successfully found {len(articles)} articles using HTML fallback")
                return articles, errors
            
            # All strategies failed
            error_msg = f"All parsing strategies failed for {rss_url}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error parsing RSS feed {rss_url}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
        
        return articles, errors
    
    async def _try_feedparser(self, rss_url: str, max_articles: int) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Try parsing with feedparser library."""
        articles = []
        errors = []
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            ) as session:
                async with session.get(rss_url) as response:
                    if response.status != 200:
                        error_msg = f"HTTP {response.status} for RSS feed {rss_url}"
                        errors.append(error_msg)
                        return articles, errors
                    
                    rss_content = await response.text()
            
            # Parse with feedparser
            feed = feedparser.parse(rss_content)
            
            if hasattr(feed, 'bozo') and feed.bozo:
                error_msg = f"RSS feed has parsing issues: {getattr(feed, 'bozo_exception', 'Unknown error')}"
                errors.append(error_msg)
                logger.warning(f"⚠️ {error_msg}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                error_msg = f"No articles found in RSS feed {rss_url}"
                errors.append(error_msg)
                return articles, errors
            
            logger.info(f"📄 Found {len(feed.entries)} entries in RSS feed")
            
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._process_feedparser_entry(entry)
                    if article:
                        articles.append(article)
                except Exception as e:
                    error_msg = f"Error processing RSS entry: {str(e)}"
                    errors.append(error_msg)
                    continue
                    
        except Exception as e:
            error_msg = f"Feedparser strategy failed: {str(e)}"
            errors.append(error_msg)
        
        return articles, errors
    
    async def _try_manual_xml_parsing(self, rss_url: str, max_articles: int) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Try manual XML parsing for malformed RSS."""
        articles = []
        errors = []
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            ) as session:
                async with session.get(rss_url) as response:
                    if response.status != 200:
                        error_msg = f"HTTP {response.status} for RSS feed {rss_url}"
                        errors.append(error_msg)
                        return articles, errors
                    
                    xml_content = await response.text()
            
            # Try to fix common XML issues
            xml_content = self._fix_xml_content(xml_content)
            
            # Parse XML manually
            root = ET.fromstring(xml_content)
            
            # Find items (RSS) or entries (Atom)
            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            if not items:
                error_msg = "No items found in XML content"
                errors.append(error_msg)
                return articles, errors
            
            logger.info(f"📄 Found {len(items)} items in XML")
            
            for item in items[:max_articles]:
                try:
                    article = self._process_xml_item(item)
                    if article:
                        articles.append(article)
                except Exception as e:
                    error_msg = f"Error processing XML item: {str(e)}"
                    errors.append(error_msg)
                    continue
                    
        except ET.ParseError as e:
            error_msg = f"XML parsing failed: {str(e)}"
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Manual XML parsing strategy failed: {str(e)}"
            errors.append(error_msg)
        
        return articles, errors
    
    async def _try_html_fallback(self, rss_url: str, max_articles: int) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Try HTML fallback to find article links."""
        articles = []
        errors = []
        
        try:
            # Convert RSS URL to base website URL
            parsed_url = urlparse(rss_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            ) as session:
                async with session.get(base_url) as response:
                    if response.status != 200:
                        error_msg = f"HTTP {response.status} for website {base_url}"
                        errors.append(error_msg)
                        return articles, errors
                    
                    html_content = await response.text()
            
            # Use BeautifulSoup to find article links
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find potential article links
            article_links = self._find_article_links(soup, base_url)
            
            if not article_links:
                error_msg = "No article links found in HTML fallback"
                errors.append(error_msg)
                return articles, errors
            
            logger.info(f"📄 Found {len(article_links)} potential article links")
            
            # Create basic article entries from links
            for i, link in enumerate(article_links[:max_articles]):
                try:
                    article = self._create_article_from_link(link, base_url)
                    if article:
                        articles.append(article)
                except Exception as e:
                    error_msg = f"Error creating article from link: {str(e)}"
                    errors.append(error_msg)
                    continue
                    
        except Exception as e:
            error_msg = f"HTML fallback strategy failed: {str(e)}"
            errors.append(error_msg)
        
        return articles, errors
    
    def _process_feedparser_entry(self, entry) -> Optional[Dict[str, Any]]:
        """Process a feedparser entry into article data."""
        try:
            title = getattr(entry, 'title', 'Untitled')
            link = getattr(entry, 'link', '')
            
            if not link:
                return None
            
            # Extract content
            content = ""
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if isinstance(entry.content, list) else str(entry.content)
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'summary'):
                content = entry.summary
            
            # Extract date
            published_date = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_date = datetime(*entry.published_parsed[:6])
                except:
                    pass
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    published_date = datetime(*entry.updated_parsed[:6])
                except:
                    pass
            
            # Extract author
            author = ""
            if hasattr(entry, 'author'):
                author = entry.author
            
            return {
                'title': title.strip(),
                'url': link.strip(),
                'content': content.strip() if content else title,
                'author': author.strip() if author else None,
                'published_date': published_date,
                'article_id': hashlib.md5(f"{link}_{title}".encode()).hexdigest()
            }
            
        except Exception as e:
            logger.error(f"Error processing feedparser entry: {str(e)}")
            return None
    
    def _process_xml_item(self, item) -> Optional[Dict[str, Any]]:
        """Process an XML item into article data."""
        try:
            # Handle both RSS and Atom formats
            title_elem = item.find('title') or item.find('.//{http://www.w3.org/2005/Atom}title')
            link_elem = item.find('link') or item.find('.//{http://www.w3.org/2005/Atom}link')
            desc_elem = item.find('description') or item.find('.//{http://www.w3.org/2005/Atom}content') or item.find('.//{http://www.w3.org/2005/Atom}summary')
            
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else 'Untitled'
            
            # Handle link
            if link_elem is not None:
                if hasattr(link_elem, 'attrib') and 'href' in link_elem.attrib:
                    link = link_elem.attrib['href']
                else:
                    link = link_elem.text.strip() if link_elem.text else ''
            else:
                return None
            
            content = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else title
            
            return {
                'title': title,
                'url': link,
                'content': content,
                'author': None,
                'published_date': datetime.now(),
                'article_id': hashlib.md5(f"{link}_{title}".encode()).hexdigest()
            }
            
        except Exception as e:
            logger.error(f"Error processing XML item: {str(e)}")
            return None
    
    def _find_article_links(self, soup, base_url: str) -> List[str]:
        """Find potential article links in HTML."""
        article_links = []
        
        # Common patterns for article links
        selectors = [
            'a[href*="/article/"]',
            'a[href*="/news/"]', 
            'a[href*="/post/"]',
            'a[href*="/story/"]',
            'a[href*="/blog/"]',
            '.article a[href]',
            '.news a[href]',
            'article a[href]'
        ]
        
        for selector in selectors:
            try:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if self._is_valid_article_url(full_url, base_url):
                            article_links.append(full_url)
            except:
                continue
        
        # Remove duplicates
        return list(dict.fromkeys(article_links))
    
    def _create_article_from_link(self, link: str, base_url: str) -> Optional[Dict[str, Any]]:
        """Create article data from a link."""
        try:
            # Extract title from URL path
            path_parts = urlparse(link).path.strip('/').split('/')
            title = path_parts[-1].replace('-', ' ').replace('_', ' ').title() if path_parts else 'Article'
            
            return {
                'title': title,
                'url': link,
                'content': title,  # Minimal content
                'author': None,
                'published_date': datetime.now(),
                'article_id': hashlib.md5(f"{link}_{title}".encode()).hexdigest()
            }
            
        except Exception as e:
            logger.error(f"Error creating article from link: {str(e)}")
            return None
    
    def _fix_xml_content(self, xml_content: str) -> str:
        """Fix common XML issues in RSS feeds."""
        try:
            # Fix unclosed tags
            xml_content = xml_content.replace('<br>', '<br/>')
            xml_content = xml_content.replace('<hr>', '<hr/>')
            xml_content = xml_content.replace('<img>', '<img/>')
            
            # Fix encoding declaration issues
            if xml_content.startswith('<?xml'):
                # Find the end of XML declaration
                end_decl = xml_content.find('?>')
                if end_decl != -1:
                    xml_content = xml_content[end_decl + 2:].lstrip()
                    xml_content = '<?xml version="1.0" encoding="UTF-8"?>' + xml_content
            
            return xml_content
            
        except Exception as e:
            logger.warning(f"Error fixing XML content: {str(e)}")
            return xml_content
    
    def _is_valid_article_url(self, url: str, base_url: str) -> bool:
        """Check if URL looks like a valid article URL."""
        try:
            parsed = urlparse(url)
            
            # Must be from same domain
            if not url.startswith(base_url):
                return False
            
            # Check for article-like patterns in path
            path = parsed.path.lower()
            article_indicators = [
                '/article/', '/news/', '/post/', '/story/', '/blog/',
                '/content/', '/press/', '/update/', '/release/'
            ]
            
            return any(indicator in path for indicator in article_indicators)
            
        except:
            return False


# Factory function for easy access
def create_robust_rss_parser(timeout: int = 30) -> RobustRSSParser:
    """Create a RobustRSSParser instance."""
    return RobustRSSParser(timeout=timeout)