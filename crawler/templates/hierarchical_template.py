"""
Hierarchical Content Extraction Template
========================================

This template implements a multi-layered content extraction system with fallback mechanisms:

1. PRIMARY: Crawl4AI (Playwright) - Modern JavaScript-heavy sites
2. SECONDARY: BeautifulSoup HTML scraping - Traditional HTML parsing  
3. TERTIARY: RSS feeds - Backup content source

The system automatically tries each method in order and reports which method succeeded.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from enum import Enum

# Import base template
from .base_template import BaseNewsSourceTemplate

# Import various extraction methods
from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
from crawler.extractors.beautifulsoup_extractor import BeautifulSoupExtractor  
from crawler.extractors.rss_extractor import RSSExtractor

# Import other services  
from crawler.templates.base_template import BaseDuplicateChecker, BaseContentProcessor, BaseContentStorage, BaseContentExtractor
from crawler.interfaces import ArticleMetadata, ProcessingResult, SourceConfig


class ExtractionMethod(Enum):
    """Enumeration of content extraction methods."""
    CRAWL4AI = "crawl4ai"
    BEAUTIFULSOUP = "beautifulsoup"
    RSS = "rss"
    FAILED = "failed"


class HierarchicalTemplate(BaseNewsSourceTemplate):
    """
    Hierarchical content extraction template with intelligent fallback system.
    
    This template tries multiple extraction methods in order:
    1. Crawl4AI (Playwright) for modern sites with JavaScript
    2. BeautifulSoup for traditional HTML parsing
    3. RSS feeds as final fallback
    
    Reports which method was successful for monitoring and optimization.
    """
    
    def __init__(self, source_config: SourceConfig):
        """Initialize hierarchical extraction template."""
        super().__init__(source_config)
        self.extraction_stats = {
            ExtractionMethod.CRAWL4AI.value: {"attempts": 0, "successes": 0},
            ExtractionMethod.BEAUTIFULSOUP.value: {"attempts": 0, "successes": 0}, 
            ExtractionMethod.RSS.value: {"attempts": 0, "successes": 0},
            ExtractionMethod.FAILED.value: {"attempts": 0, "successes": 0}
        }
        
        logger.info(f"Initialized hierarchical extraction for {source_config.name}")
        
    def _create_discovery_service(self):
        """Create hierarchical discovery service."""
        return HierarchicalDiscoveryService(self.config)
        
    def _create_extractor_service(self):
        """Create hierarchical extractor service."""
        return HierarchicalExtractorService(self.config)
        
    def _create_processor_service(self):
        """Create content processor service.""" 
        return BaseContentProcessor(self.config)
        
    def _create_duplicate_checker(self):
        """Create duplicate checker service."""
        return BaseDuplicateChecker(self.config)
        
    def _create_storage_service(self):
        """Create storage service."""
        return BaseContentStorage(self.config)
        
    async def fetch_articles(self, max_articles: Optional[int] = None) -> List[ArticleMetadata]:
        """
        Fetch articles using hierarchical extraction methods.
        
        Tries each extraction method in order until one succeeds.
        Reports which method was used for transparency.
        """
        max_articles = max_articles or self.config.max_articles_per_run
        logger.info(f"Starting hierarchical extraction for {self.config.name} (max: {max_articles})")
        
        # Try each extraction method in order
        extraction_methods = [
            (ExtractionMethod.CRAWL4AI, self._try_crawl4ai_extraction),
            (ExtractionMethod.BEAUTIFULSOUP, self._try_beautifulsoup_extraction),
            (ExtractionMethod.RSS, self._try_rss_extraction)
        ]
        
        for method, extractor_func in extraction_methods:
            try:
                logger.info(f"🔄 Trying {method.value} extraction for {self.config.name}")
                self.extraction_stats[method.value]["attempts"] += 1
                
                articles = await extractor_func(max_articles)
                
                if articles and len(articles) > 0:
                    self.extraction_stats[method.value]["successes"] += 1
                    logger.success(f"✅ {method.value} extraction succeeded for {self.config.name} - found {len(articles)} articles")
                    
                    # Store extraction method info for reporting (can't modify frozen dataclass)
                    # The extraction method will be tracked in the template's statistics instead
                    
                    return articles
                else:
                    logger.warning(f"⚠️ {method.value} extraction returned no articles for {self.config.name}")
                    
            except Exception as e:
                logger.error(f"❌ {method.value} extraction failed for {self.config.name}: {str(e)}")
                continue
        
        # All methods failed
        self.extraction_stats[ExtractionMethod.FAILED.value]["attempts"] += 1
        logger.error(f"🚨 All extraction methods failed for {self.config.name}")
        return []    
    async def _try_crawl4ai_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using Crawl4AI (Playwright)."""
        # Delegate to discovery service
        discovery_service = self.get_discovery_service()
        return await discovery_service._try_crawl4ai_extraction(max_articles)    
    async def _try_beautifulsoup_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using BeautifulSoup.""" 
        # Delegate to discovery service
        discovery_service = self.get_discovery_service()
        return await discovery_service._try_beautifulsoup_extraction(max_articles)    
    async def _try_rss_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using RSS feeds."""
        # Delegate to discovery service
        discovery_service = self.get_discovery_service()
        return await discovery_service._try_rss_extraction(max_articles)
    
    async def _discover_rss_feed(self) -> Optional[str]:
        """Try to discover RSS feed URLs automatically."""
        try:
            common_rss_paths = ["/feed/", "/rss/", "/feed.xml", "/rss.xml", "/feed.rss", "/atom.xml"]
            base_url = self.config.base_url.rstrip('/')
            
            # Simple HTTP check for common RSS paths
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for path in common_rss_paths:
                    test_url = f"{base_url}{path}"
                    try:
                        async with session.get(test_url, timeout=10) as response:
                            if response.status == 200:
                                content_type = response.headers.get('content-type', '').lower()
                                if any(t in content_type for t in ['xml', 'rss', 'atom']):
                                    logger.info(f"Discovered RSS feed: {test_url}")
                                    return test_url
                    except:
                        continue
        except Exception as e:
            logger.warning(f"RSS discovery failed: {str(e)}")
        return None    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about extraction method usage."""
        stats = {}
        total_attempts = sum(method["attempts"] for method in self.extraction_stats.values())
        
        for method, data in self.extraction_stats.items():
            attempts = data["attempts"]
            successes = data["successes"] 
            
            stats[method] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate": (successes / attempts * 100) if attempts > 0 else 0,
                "usage_percent": (attempts / total_attempts * 100) if total_attempts > 0 else 0
            }
            
    async def health_check(self) -> bool:
        """
        Override the health check to work properly with hierarchical template.
        """
        try:
            # Try a simple extraction test instead of using the buggy discovery service
            articles = await self.fetch_articles(max_articles=1)
            return len(articles) > 0
        except Exception as e:
            logger.error(f"Health check failed for {self.config.name}: {str(e)}")
            return False


class HierarchicalDiscoveryService:
    """Article discovery service for hierarchical template."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        
    async def discover_articles(self, max_articles: int = 50):
        """Discover article URLs using the best available method."""
        # Use the same hierarchical extraction logic as in fetch_articles
        try:
            # Try each extraction method in order
            extraction_methods = [
                ("crawl4ai", self._try_crawl4ai_extraction),
                ("beautifulsoup", self._try_beautifulsoup_extraction),
                ("rss", self._try_rss_extraction)
            ]
            
            for method_name, extractor_func in extraction_methods:
                try:
                    logger.info(f"🔄 Discovery trying {method_name} for {self.config.name}")
                    articles = await extractor_func(max_articles)
                    
                    if articles and len(articles) > 0:
                        logger.success(f"✅ Discovery using {method_name} found {len(articles)} articles for {self.config.name}")
                        
                        # Yield each discovered article
                        for article in articles:
                            yield article
                        return  # Successfully found articles, stop trying other methods
                    else:
                        logger.warning(f"⚠️ Discovery {method_name} returned no articles for {self.config.name}")
                        
                except Exception as e:
                    logger.error(f"❌ Discovery {method_name} failed for {self.config.name}: {str(e)}")
                    continue
            
            # If we reach here, all methods failed
            logger.error(f"🚨 All discovery methods failed for {self.config.name}")
            
        except Exception as e:
            logger.error(f"Discovery service error for {self.config.name}: {e}")
    
    async def _try_crawl4ai_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using Crawl4AI (Playwright)."""
        try:
            from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
            from crawler.extractors.rss_extractor import RSSExtractor
            
            extractor = EnhancedCrawl4AIExtractor(self.config)
            
            # For RSS-configured sources, first discover article URLs via RSS
            if self.config.rss_url:
                # Use RSS to find article URLs, then crawl with Crawl4AI
                rss_extractor = RSSExtractor(self.config)
                article_urls = await rss_extractor.discover_article_urls(max_articles)
                
                articles = []
                for url in article_urls[:max_articles]:
                    try:
                        article = await extractor.extract_article_content(url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to extract {url} with Crawl4AI: {str(e)}")
                        continue
                        
                return articles
            else:
                # Direct website crawling for HTML scraping sources
                return await extractor.crawl_website(self.config.base_url, max_articles)
                
        except Exception as e:
            logger.error(f"Crawl4AI extraction error: {str(e)}")
            raise
    
    async def _try_beautifulsoup_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using BeautifulSoup."""
        try:
            from crawler.extractors.beautifulsoup_extractor import BeautifulSoupExtractor
            from crawler.extractors.rss_extractor import RSSExtractor
            
            extractor = BeautifulSoupExtractor(self.config)
            
            # Similar approach - use RSS for URL discovery if available
            if self.config.rss_url:
                rss_extractor = RSSExtractor(self.config)
                article_urls = await rss_extractor.discover_article_urls(max_articles)
                
                articles = []
                for url in article_urls[:max_articles]:
                    try:
                        article = await extractor.extract_article_content(url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to extract {url} with BeautifulSoup: {str(e)}")
                        continue
                        
                return articles
            else:
                # Direct website scraping for HTML scraping sources
                return await extractor.scrape_website(self.config.base_url, max_articles)
                
        except Exception as e:
            logger.error(f"BeautifulSoup extraction error: {str(e)}")
            raise
    
    async def _try_rss_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using RSS feeds."""
        try:
            from crawler.extractors.rss_extractor import RSSExtractor
            
            if not self.config.rss_url:
                # Try to discover RSS feed automatically
                rss_url = await self._discover_rss_feed()
                if not rss_url:
                    raise Exception("No RSS feed configured or discovered")
            else:
                rss_url = self.config.rss_url
            
            extractor = RSSExtractor(self.config, rss_url)
            return await extractor.extract_from_rss(max_articles)
            
        except Exception as e:
            logger.error(f"RSS extraction error: {str(e)}")
            raise
    
    async def _discover_rss_feed(self) -> Optional[str]:
        """Try to discover RSS feed URLs automatically."""
        try:
            common_rss_paths = ["/feed/", "/rss/", "/feed.xml", "/rss.xml", "/feed.rss", "/atom.xml"]
            base_url = self.config.base_url.rstrip('/')
            
            # Simple HTTP check for common RSS paths
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for path in common_rss_paths:
                    test_url = f"{base_url}{path}"
                    try:
                        async with session.get(test_url, timeout=10) as response:
                            if response.status == 200:
                                content_type = response.headers.get('content-type', '').lower()
                                if any(t in content_type for t in ['xml', 'rss', 'atom']):
                                    logger.info(f"Discovered RSS feed: {test_url}")
                                    return test_url
                    except:
                        continue
        except Exception as e:
            logger.warning(f"RSS discovery failed: {str(e)}")
        return None


class HierarchicalExtractorService: 
    """Content extraction service for hierarchical template."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract content using the best available method."""
        return None


class HierarchicalExtractorService(BaseContentExtractor):
    """Hierarchical content extraction service with multiple fallback methods."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.extraction_stats = {
            "crawl4ai": {"attempts": 0, "successes": 0},
            "beautifulsoup": {"attempts": 0, "successes": 0},
            "rss": {"attempts": 0, "successes": 0}
        }
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """
        Extract content using hierarchical fallback methods.
        
        Tries multiple extraction methods in order:
        1. Crawl4AI (best for JavaScript-heavy sites)
        2. BeautifulSoup (traditional HTML parsing)  
        3. RSS content (fallback)
        """
        try:
            # Method 1: Try Crawl4AI extraction
            result = await self._try_crawl4ai_content_extraction(article_meta)
            if result and result.success:
                self.extraction_stats["crawl4ai"]["successes"] += 1
                logger.success(f"Crawl4AI content extraction succeeded for {article_meta.title[:50]}...")
                return result
            
            # Method 2: Try BeautifulSoup extraction
            result = await self._try_beautifulsoup_content_extraction(article_meta)
            if result and result.success:
                self.extraction_stats["beautifulsoup"]["successes"] += 1
                logger.success(f"BeautifulSoup content extraction succeeded for {article_meta.title[:50]}...")
                return result
            
            # Method 3: Try RSS content extraction (if available)
            result = await self._try_rss_content_extraction(article_meta)
            if result and result.success:
                self.extraction_stats["rss"]["successes"] += 1
                logger.success(f"RSS content extraction succeeded for {article_meta.title[:50]}...")
                return result
            
            # All methods failed
            logger.error(f"All content extraction methods failed for {article_meta.title[:50]}...")
            return ProcessingResult(
                success=False,
                error=f"All extraction methods failed for article: {article_meta.title}",
                content="",
                metadata={"extraction_method": "failed", "attempts": ["crawl4ai", "beautifulsoup", "rss"]}
            )
            
        except Exception as e:
            logger.error(f"Critical error in hierarchical content extraction: {str(e)}")
            return ProcessingResult(
                success=False,
                error=f"Critical extraction error: {str(e)}",
                content="",
                metadata={"extraction_method": "error", "error": str(e)}
            )
    
    async def _try_crawl4ai_content_extraction(self, article_meta: ArticleMetadata) -> Optional[ProcessingResult]:
        """Try extracting content using Enhanced Crawl4AI with timeout handling."""
        try:
            self.extraction_stats["crawl4ai"]["attempts"] += 1
            
            # Import and initialize ENHANCED Crawl4AI extractor (with timeout fixes)
            from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
            extractor = EnhancedCrawl4AIExtractor(self.config)
            
            # Use the enhanced extractor's timeout-aware article extraction
            article = await extractor.extract_article_content(article_meta.url)
            
            if article and hasattr(article, 'content'):
                # If article has content, extract it
                content = getattr(article, 'content', '')
                if content and len(content.strip()) > 100:
                    logger.success(f"✅ Enhanced Crawl4AI extracted content for {article_meta.url} ({len(content)} chars)")
                    return ProcessingResult(
                        success=True,
                        content=content,
                        metadata={
                            "extraction_method": "enhanced_crawl4ai",
                            "content_length": len(content),
                            "url": article_meta.url,
                            "title": getattr(article, 'title', '')
                        }
                    )
            
            logger.warning(f"⚠️ Enhanced Crawl4AI extracted insufficient content for {article_meta.url}")
            return None
                
        except Exception as e:
            logger.error(f"Crawl4AI content extraction failed: {str(e)}")
            return None
    
    async def _try_beautifulsoup_content_extraction(self, article_meta: ArticleMetadata) -> Optional[ProcessingResult]:
        """Try extracting content using BeautifulSoup."""
        try:
            self.extraction_stats["beautifulsoup"]["attempts"] += 1
            
            # Import and initialize BeautifulSoup extractor  
            from crawler.extractors.beautifulsoup_extractor import BeautifulSoupExtractor
            extractor = BeautifulSoupExtractor(self.config)
            
            # Try custom extraction method first
            if hasattr(extractor, '_extract_article_content'):
                content = await extractor._extract_article_content(article_meta.url)
            else:
                # Fallback to basic HTTP request + BeautifulSoup parsing
                import aiohttp
                from bs4 import BeautifulSoup
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(article_meta.url, headers=headers, timeout=10) as response:
                        if response.status != 200:
                            return None
                        html = await response.text()
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    element.decompose()
                
                # Try common content selectors
                content_selectors = ['article', '[role="main"]', '.post-content', '.article-content', 'main']
                
                content = None
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        content = elements[0].get_text(strip=True)
                        if len(content) > 100:
                            break
                
                # Fallback to body text
                if not content or len(content) < 100:
                    body = soup.find('body')
                    if body:
                        content = body.get_text(strip=True)
            
            if content and len(content.strip()) > 100:  # Minimum content threshold
                return ProcessingResult(
                    success=True,
                    content=content,
                    metadata={
                        "extraction_method": "beautifulsoup",
                        "content_length": len(content),
                        "url": article_meta.url
                    }
                )
            else:
                logger.warning(f"BeautifulSoup extracted insufficient content for {article_meta.url}")
                return None
                
        except Exception as e:
            logger.error(f"BeautifulSoup content extraction failed: {str(e)}")
            return None
    
    async def _try_rss_content_extraction(self, article_meta: ArticleMetadata) -> Optional[ProcessingResult]:
        """Try extracting content from RSS description/summary."""
        try:
            self.extraction_stats["rss"]["attempts"] += 1
            
            # Use RSS description/summary as fallback content
            content = getattr(article_meta, 'description', None) or getattr(article_meta, 'summary', None)
            
            if content and len(content.strip()) > 50:  # Lower threshold for RSS content
                return ProcessingResult(
                    success=True,
                    content=content,
                    metadata={
                        "extraction_method": "rss_description",
                        "content_length": len(content),
                        "url": article_meta.url
                    }
                )
            else:
                logger.warning(f"No usable RSS content for {article_meta.url}")
                return None
                
        except Exception as e:
            logger.error(f"RSS content extraction failed: {str(e)}")
            return None
