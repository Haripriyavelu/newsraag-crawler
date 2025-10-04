"""
RSS extractor for RSS/Atom feeds.

Handles RSS feed parsing and article discovery.
"""

import asyncio
import aiohttp
import feedparser
from typing import List, Optional, Dict, Any
from loguru import logger
from crawler.interfaces import ArticleMetadata, SourceConfig
from datetime import datetime
import hashlib


class RSSExtractor:
    """Content extractor for RSS feeds."""
    
    def __init__(self, config: SourceConfig, rss_url: str = None):
        self.config = config
        self.rss_url = rss_url or getattr(config, 'rss_url', None)
        
        if not self.rss_url:
            raise ValueError("RSS URL is required for RSS extractor")
    
    async def extract_from_rss(self, max_articles: int) -> List[ArticleMetadata]:
        """Extract articles from RSS feed."""
        articles = []
        
        try:
            logger.info(f"📡 Fetching RSS feed: {self.rss_url}")
            
            # Fetch RSS content
            async with aiohttp.ClientSession() as session:
                async with session.get(self.rss_url, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} for RSS feed {self.rss_url}")
                        return []
                    
                    rss_content = await response.text()
            
            # Parse RSS feed
            feed = feedparser.parse(rss_content)
            
            if hasattr(feed, 'bozo') and feed.bozo:
                logger.warning(f"RSS feed has parsing issues: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"No articles found in RSS feed {self.rss_url}")
                return []
            
            logger.info(f"Found {len(feed.entries)} articles in RSS feed")
            
            # Process entries
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._process_rss_entry(entry)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to process RSS entry: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"RSS extraction error for {self.rss_url}: {str(e)}")
            raise
        
        logger.info(f"✅ RSS extracted {len(articles)} articles from {self.rss_url}")
        return articles
    
    def _process_rss_entry(self, entry) -> Optional[ArticleMetadata]:
        """Process a single RSS entry into ArticleMetadata."""
        try:
            # Extract basic information
            title = getattr(entry, 'title', 'Untitled')
            url = getattr(entry, 'link', '')
            
            if not url:
                logger.warning("RSS entry missing URL")
                return None
            
            # Extract content
            content = ""
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if isinstance(entry.content, list) else entry.content
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'summary'):
                content = entry.summary
            
            if not content or len(content.strip()) < 50:
                logger.warning(f"RSS entry has insufficient content: {len(content)} chars")
                # Don't return None here - some RSS feeds have minimal content
                content = title  # Use title as fallback content
            
            # Extract date as datetime object
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
            elif hasattr(entry, 'authors') and entry.authors:
                author = entry.authors[0].get('name', '') if isinstance(entry.authors, list) else str(entry.authors)
            
            # Extract tags/categories
            tags = []
            if hasattr(entry, 'tags') and entry.tags:
                tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            
            # Generate article ID
            article_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title,
                url=url,
                published_date=published_date,
                source_name=self.config.name,
                article_id=article_id,
                author=author,
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"Error processing RSS entry: {str(e)}")
            return None
    
    async def discover_article_urls(self, max_articles: int) -> List[str]:
        """Discover article URLs from RSS feed."""
        try:
            articles = await self.extract_from_rss(max_articles)
            return [article.url for article in articles if article.url]
        except Exception as e:
            logger.error(f"Error discovering article URLs: {str(e)}")
            return []
    
    async def health_check(self) -> bool:
        """Check if RSS extractor is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.rss_url, timeout=10) as response:
                    if response.status != 200:
                        return False
                    
                    rss_content = await response.text()
                    feed = feedparser.parse(rss_content)
                    
                    # Check if feed has entries
                    return hasattr(feed, 'entries') and len(feed.entries) > 0
                    
        except Exception as e:
            logger.error(f"RSS health check failed: {str(e)}")
            return False