# crawler/templates/rss_template.py
"""
RSS Template implementation for RSS-based news sources.
Provides reusable RSS parsing and content extraction logic.
"""
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    print("Warning: feedparser not available, RSS functionality limited")
    FEEDPARSER_AVAILABLE = False

import hashlib
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime, timezone

from crawler.templates.base_template import (
    BaseNewsSourceTemplate, BaseArticleDiscovery, BaseContentExtractor,
    BaseContentProcessor, BaseDuplicateChecker, BaseContentStorage
)
from crawler.interfaces.news_source_interface import (
    SourceConfig, ArticleMetadata, ProcessingResult,
    IArticleDiscovery, IContentExtractor, IContentProcessor,
    IDuplicateChecker, IContentStorage,
    SourceDiscoveryError, ContentExtractionError
)


class RSSArticleDiscovery(BaseArticleDiscovery):
    """RSS-based article discovery service."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        if not config.rss_url:
            raise ValueError(f"RSS URL is required for RSS source: {config.name}")
    
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles from RSS feed."""
        try:
            print(f"Fetching RSS feed for {self.config.name}: {self.config.rss_url}")
            
            # Parse RSS feed
            feed = await self._parse_rss_feed()
            
            if not feed.entries:
                print(f"No articles found in RSS feed for {self.config.name}")
                return
            
            print(f"Found {len(feed.entries)} articles in RSS feed for {self.config.name}")
            
            # Convert RSS entries to ArticleMetadata
            articles_yielded = 0
            for entry in feed.entries:
                try:
                    article_meta = self._convert_entry_to_metadata(entry)
                    if article_meta:
                        articles_yielded += 1
                        yield article_meta
                        
                        # Respect max articles limit
                        if articles_yielded >= self.config.max_articles_per_run:
                            print(f"Reached max articles limit for {self.config.name}")
                            break
                            
                except Exception as e:
                    print(f"Failed to convert RSS entry to metadata: {e}")
                    continue
            
            print(f"Yielded {articles_yielded} articles for {self.config.name}")
            
        except Exception as e:
            print(f"RSS discovery failed for {self.config.name}: {e}")
            raise SourceDiscoveryError(f"RSS feed parsing failed: {e}", self.config.name)
    
    async def _parse_rss_feed(self) -> Any:
        """Parse RSS feed with error handling."""
        if not FEEDPARSER_AVAILABLE:
            raise SourceDiscoveryError("feedparser not available", self.config.name)
            
        try:
            # For now, use feedparser directly (can be enhanced with aiohttp later)
            feed = feedparser.parse(self.config.rss_url)
            
            if feed.bozo:
                print(f"RSS feed has parsing issues for {self.config.name}: {feed.bozo_exception}")
            
            return feed
            
        except Exception as e:
            raise SourceDiscoveryError(f"Failed to parse RSS feed: {e}", self.config.name)
    
    def _convert_entry_to_metadata(self, entry) -> Optional[ArticleMetadata]:
        """Convert RSS entry to ArticleMetadata."""
        try:
            # Extract basic information
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()
            
            if not title or not link:
                print(f"Skipping entry with missing title or link")
                return None
            
            # Parse publication date
            pub_date = self._parse_publication_date(entry)
            
            # Generate article ID
            article_id = self._generate_article_id(title, link)
            
            # Extract additional metadata
            author = entry.get('author', entry.get('dc_creator', None))
            category = self._extract_category(entry)
            tags = self._extract_tags(entry)
            
            return ArticleMetadata(
                title=title,
                url=link,
                published_date=pub_date,
                source_name=self.config.name,
                article_id=article_id,
                author=author,
                category=category,
                language="en",  # Default, can be detected later
                tags=tags
            )
            
        except Exception as e:
            print(f"Failed to convert RSS entry: {e}")
            return None
    
    def _parse_publication_date(self, entry) -> datetime:
        """Parse publication date from RSS entry."""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and entry[field]:
                try:
                    import time
                    timestamp = time.mktime(entry[field])
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                except Exception:
                    continue
        
        # Try string date fields
        date_string_fields = ['published', 'updated', 'created']
        for field in date_string_fields:
            if hasattr(entry, field) and entry[field]:
                try:
                    from dateutil import parser
                    return parser.parse(entry[field])
                except Exception:
                    continue
        
        # Default to current time
        print(f"Could not parse publication date for entry, using current time")
        return datetime.now(timezone.utc)
    
    def _generate_article_id(self, title: str, url: str) -> str:
        """Generate unique article ID."""
        content_for_id = f"{self.config.name}:{title}:{url}"
        return hashlib.md5(content_for_id.encode()).hexdigest()
    
    def _extract_category(self, entry) -> Optional[str]:
        """Extract category from RSS entry."""
        if hasattr(entry, 'category'):
            return entry.category
        
        if hasattr(entry, 'tags') and entry.tags:
            # Use first tag as category
            return entry.tags[0].get('term', None)
        
        return self.config.content_type.value  # Default to source content type
    
    def _extract_tags(self, entry) -> Optional[list]:
        """Extract tags from RSS entry."""
        tags = []
        
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if 'term' in tag:
                    tags.append(tag['term'])
        
        return tags if tags else None


class RSSContentExtractor(BaseContentExtractor):
    """RSS-based content extraction using Crawl4AI."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self._browser_config = self._create_browser_config()
    
    def _create_browser_config(self):
        """Create browser configuration for Crawl4AI."""
        # Simple config for now, can be enhanced with BrowserConfig later
        return {
            "headless": True,
            "args": [
                "--disable-gpu",
                "--disable-dev-shm-usage", 
                "--no-sandbox",
                "--disable-extensions"
            ]
        }
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content from article URL using Crawl4AI."""
        try:
            print(f"Extracting content from: {article_meta.url}")
            
            # For Phase 1, use a simple implementation
            # TODO: Integrate with actual Crawl4AI in Phase 2
            content = await self._simple_content_extraction(article_meta.url)
            
            if not content or len(content.strip()) < 100:
                raise ContentExtractionError(
                    "Extracted content is too short or empty",
                    self.config.name
                )
            
            print(f"Extracted {len(content)} characters from {article_meta.url}")
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata={
                    'extraction_method': 'simple_extraction',
                    'content_length': len(content),
                    'url': article_meta.url
                }
            )
                
        except Exception as e:
            print(f"Content extraction failed for {article_meta.url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    async def _simple_content_extraction(self, url: str) -> str:
        """Simple content extraction - placeholder for Phase 1."""
        try:
            import requests
            response = requests.get(url, timeout=self.config.timeout_seconds)
            response.raise_for_status()
            
            # Basic HTML parsing
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for element in soup(["script", "style", "nav", "header", "footer"]):
                    element.decompose()
                
                # Get text content
                content = soup.get_text(separator=' ', strip=True)
                return content
            except ImportError:
                # Fallback to simple text extraction if BeautifulSoup not available
                return response.text
            
        except Exception as e:
            raise ContentExtractionError(f"Simple content extraction failed: {e}", self.config.name)


class RSSNewsSourceTemplate(BaseNewsSourceTemplate):
    """Complete RSS template combining all RSS-specific services."""
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        """Create RSS article discovery service."""
        return RSSArticleDiscovery(self.config)
    
    def _create_extractor_service(self) -> IContentExtractor:
        """Create RSS content extraction service."""
        return RSSContentExtractor(self.config)
    
    def _create_processor_service(self) -> IContentProcessor:
        """Create content processing service (reuse base implementation)."""
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self) -> IDuplicateChecker:
        """Create duplicate checking service (reuse base implementation)."""
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self) -> IContentStorage:
        """Create storage service (reuse base implementation)."""
        return BaseContentStorage(self.config)
    
    async def _perform_health_check(self) -> bool:
        """RSS-specific health check."""
        try:
            # Test RSS feed accessibility
            discovery_service = self.get_discovery_service()
            
            # Try to fetch RSS feed (but don't process all articles)
            async for article in discovery_service.discover_articles():
                # If we can get at least one article, RSS feed is accessible
                return True
            
            return False  # No articles found
            
        except Exception as e:
            print(f"RSS health check failed for {self.config.name}: {e}")
            return False


# Factory function for easy RSS source creation
def create_rss_source(source_config: SourceConfig) -> RSSNewsSourceTemplate:
    """Create an RSS news source from configuration."""
    if source_config.source_type.value != "rss":
        raise ValueError(f"Source type must be 'rss', got: {source_config.source_type.value}")
    
    return RSSNewsSourceTemplate(source_config)
