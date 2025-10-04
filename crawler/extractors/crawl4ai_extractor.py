"""
Enhanced Crawl4AI extractor with robust timeout handling and fallback strategies.
Fixes FXStreet timeout issues and provides better reliability for financial news sites.
"""

import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy, NoExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking
from crawler.interfaces import ArticleMetadata, SourceConfig
from datetime import datetime
import hashlib
import time
import atexit

# SINGLE BROWSER POOL - ONLY ONE CHROME PROCESS FOR ALL SOURCES
class SingleBrowserPool:
    """Single browser instance shared across ALL sources."""
    
    _instance = None
    _crawler = None
    _initialized = False
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        atexit.register(self.cleanup_sync)
        logger.info("Single browser pool initialized - ONE Chrome for all sources")
    
    async def get_global_browser(self) -> AsyncWebCrawler:
        """Get the single global browser instance for all sources."""
        async with self._lock:
            if self._crawler is None:
                await self._create_single_browser()
            return self._crawler
    
    async def _create_single_browser(self):
        """Create the single browser instance for all sources."""
        try:
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                viewport_width=1280,
                viewport_height=720,
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--memory-pressure-off",
                    "--max-old-space-size=512",  # Higher for single browser
                    "--aggressive-cache-discard",
                    "--disable-background-timer-throttling",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                ]
            )
            
            self._crawler = AsyncWebCrawler(config=browser_config, verbose=False)
            await self._crawler.astart()
            
            logger.info("Created SINGLE global browser for ALL 29 sources")
            
        except Exception as e:
            logger.error(f"Failed to create single browser: {e}")
            raise
    
    def cleanup_sync(self):
        """Cleanup single browser on exit."""
        try:
            if self._crawler:
                import asyncio
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._crawler.aclose())
                logger.info("Single global browser cleaned up")
        except:
            pass

# Global single browser instance
_single_browser_pool = SingleBrowserPool()


class EnhancedCrawl4AIExtractor:
    """
    Enhanced content extractor using Crawl4AI with intelligent timeout handling.
    
    Features:
    - Configurable timeouts per source
    - Multiple retry strategies  
    - Fallback to lighter extraction modes
    - Anti-bot detection countermeasures
    """
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.crawler = None
        self.max_retries = 3
        self.retry_timeouts = [30, 60, 120]  # Progressive timeout increase
        self._initialize_crawler()
    
    def _initialize_crawler(self):
        """Initialize the Crawl4AI extractor to use SINGLE global browser only."""
        # DO NOT create individual browser instances - use the single global browser pool
        self.crawler = None  # Always None - we use the global browser pool
        logger.info(f"Enhanced Crawl4AI extractor initialized for {self.config.name} - using SINGLE global browser")
    
    async def crawl_website(self, base_url: str, max_articles: int) -> List[ArticleMetadata]:
        """Crawl website using the SINGLE global browser shared by all sources."""
        articles = []
        
        try:
            logger.info(f"🚀 Starting enhanced crawl of {base_url} for {self.config.name} using SINGLE browser")
            
            # Get the SINGLE global browser instance (shared by ALL sources)
            crawler = await _single_browser_pool.get_global_browser()
            
            # Try progressive timeout strategy
            for attempt, timeout_seconds in enumerate(self.retry_timeouts, 1):
                try:
                    logger.info(f"📡 Attempt {attempt}/{len(self.retry_timeouts)} with {timeout_seconds}s timeout for {self.config.name}")
                    
                    # Configure crawl settings with timeout
                    config = self._create_crawl_config(timeout_seconds)
                    
                    # Perform the crawl with timeout using SINGLE browser
                    result = await asyncio.wait_for(
                        crawler.arun(url=base_url, config=config),
                        timeout=timeout_seconds + 10  # Add 10s buffer for cleanup
                    )
                    
                    if result.success:
                        logger.success(f"✅ {self.config.name}: Successfully crawled {base_url} on attempt {attempt}")
                        
                        # Extract article information
                        article = self._process_crawl_result(result, base_url)
                        if article:
                            articles.append(article)
                            
                        # Try to find additional article links
                        if hasattr(result, 'links') and result.links:
                            article_links = self._filter_article_links(result.links, base_url)
                            
                            for link_url in article_links[:max_articles-1]:  # -1 because we already have the main page
                                try:
                                    # Use shorter timeout for individual articles with SINGLE browser
                                    article_timeout = min(timeout_seconds, 45)
                                    link_result = await asyncio.wait_for(
                                        crawler.arun(url=link_url, config=config),
                                        timeout=article_timeout
                                    )
                                    
                                    if link_result.success:
                                        article = self._process_crawl_result(link_result, link_url)
                                        if article:
                                            articles.append(article)
                                except asyncio.TimeoutError:
                                    logger.warning(f"⏰ {self.config.name}: Article timeout for {link_url}")
                                    continue
                                except Exception as e:
                                    logger.warning(f"⚠️ {self.config.name}: Failed to crawl article {link_url}: {str(e)}")
                                    continue
                        
                        # Success - break retry loop
                        break
                        
                    else:
                        logger.warning(f"⚠️ {self.config.name}: Crawl failed on attempt {attempt}: {result.error_message}")
                        if attempt == len(self.retry_timeouts):
                            raise Exception(f"All crawl attempts failed. Last error: {result.error_message}")
                        continue
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ {self.config.name}: Timeout after {timeout_seconds}s on attempt {attempt}")
                    if attempt == len(self.retry_timeouts):
                        logger.error(f"❌ {self.config.name}: All timeout attempts exhausted for {base_url}")
                        raise Exception(f"Crawl timeout after all retry attempts ({self.retry_timeouts})")
                    continue
                    
                except Exception as e:
                    logger.error(f"❌ {self.config.name}: Crawl error on attempt {attempt}: {str(e)}")
                    if attempt == len(self.retry_timeouts):
                        raise
                    continue
                
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Enhanced crawl extraction error: {str(e)}")
            raise
            
        logger.info(f"✅ {self.config.name}: Enhanced crawl extracted {len(articles)} articles from {base_url}")
        return articles
    
    def _create_crawl_config(self, timeout_seconds: int) -> CrawlerRunConfig:
        """Create crawl configuration with timeout and extraction strategy."""
        # Use lighter extraction for faster loading
        extraction_strategy = NoExtractionStrategy()  
        chunking_strategy = RegexChunking()
        
        return CrawlerRunConfig(
            word_count_threshold=50,
            extraction_strategy=extraction_strategy,
            chunking_strategy=chunking_strategy,
            cache_mode=CacheMode.BYPASS,
            # Timeout configuration
            page_timeout=timeout_seconds * 1000,  # Convert to milliseconds
            # Anti-detection
            simulate_user=True,
            override_navigator=True
        )
    
    def _process_crawl_result(self, result, url: str) -> Optional[ArticleMetadata]:
        """Process crawl result into ArticleMetadata with enhanced validation."""
        try:
            # Extract content with multiple fallback strategies
            content = ""
            
            if hasattr(result, 'markdown') and result.markdown:
                content = result.markdown
            elif hasattr(result, 'cleaned_html') and result.cleaned_html:
                content = result.cleaned_html  
            elif hasattr(result, 'html') and result.html:
                # Basic HTML cleanup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'html.parser')
                content = soup.get_text(separator=' ', strip=True)
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"⚠️ {self.config.name}: Content too short from {url}: {len(content)} chars")
                return None
            
            # Extract metadata with fallbacks
            title = ""
            if hasattr(result, 'metadata') and result.metadata:
                title = result.metadata.get('title', '')
            
            if not title and hasattr(result, 'title'):
                title = result.title
                
            # Extract from HTML if still no title
            if not title and hasattr(result, 'html'):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.html, 'html.parser')
                    title_tag = soup.find('title') or soup.find('h1') or soup.find('h2')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                except:
                    pass
                    
            # Generate article ID
            article_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()
            
            logger.debug(f"📄 {self.config.name}: Processed article - Title: {title[:50]}..., Content: {len(content)} chars")
            
            return ArticleMetadata(
                title=title or f"Article from {url}",
                url=url,
                published_date=datetime.now(),
                source_name=self.config.name,
                article_id=article_id
            )
            
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Error processing crawl result for {url}: {str(e)}")
            return None
    
    def _filter_article_links(self, links: List[str], base_url: str) -> List[str]:
        """Filter and prioritize article links with enhanced patterns."""
        article_links = []
        
        # Enhanced article URL patterns for financial sites
        article_patterns = [
            '/article/', '/news/', '/post/', '/blog/', '/story/',
            '/analysis/', '/market/', '/forex/', '/stock/', '/trading/',
            '/research/', '/insight/', '/commentary/', '/opinion/',
            '/technical-analysis/', '/fundamental-analysis/',
            # FXStreet specific patterns
            '/usd-', '/eur-', '/gbp-', '/jpy-', '/cad-', '/aud-', '/chf-', '/nzd-'
        ]
        
        # Skip patterns (ads, social, etc.)
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/advertorial/',
            'facebook.com', 'twitter.com', 'linkedin.com', 'youtube.com',
            '/subscribe', '/newsletter', '/contact', '/about'
        ]
        
        for link in links:
            try:
                # Skip external links
                if not link.startswith(base_url) and not link.startswith('/'):
                    continue
                
                # Skip unwanted patterns
                if any(pattern in link.lower() for pattern in skip_patterns):
                    continue
                
                # Check if URL looks like an article
                if any(pattern in link.lower() for pattern in article_patterns):
                    # Make URL absolute
                    if link.startswith('/'):
                        link = base_url.rstrip('/') + link
                    article_links.append(link)
                    
            except Exception as e:
                logger.warning(f"⚠️ {self.config.name}: Error filtering link {link}: {str(e)}")
                continue
                
        # Remove duplicates and limit
        unique_links = list(dict.fromkeys(article_links))  # Preserves order
        logger.debug(f"🔗 {self.config.name}: Filtered {len(unique_links)} article links from {len(links)} total links")
        
        return unique_links[:20]  # Limit to avoid too many requests
    
    async def extract_article_content(self, url: str) -> Optional[ArticleMetadata]:
        """Extract content using the SINGLE global browser shared by all sources."""
        try:
            # Get the SINGLE global browser instance (shared by ALL sources)
            crawler = await _single_browser_pool.get_global_browser()
            
            # Use progressive timeout for individual articles
            for attempt, timeout_seconds in enumerate([30, 60, 90], 1):
                try:
                    logger.debug(f"📄 {self.config.name}: Extracting {url} (attempt {attempt}, timeout {timeout_seconds}s) using SINGLE browser")
                    
                    config = self._create_crawl_config(timeout_seconds)
                    
                    result = await asyncio.wait_for(
                        crawler.arun(url=url, config=config),
                        timeout=timeout_seconds + 5
                    )
                    
                    if result.success:
                        logger.debug(f"✅ {self.config.name}: Successfully extracted {url} using SINGLE browser")
                        return self._process_crawl_result(result, url)
                    else:
                        logger.warning(f"⚠️ {self.config.name}: Article extraction failed on attempt {attempt}: {result.error_message}")
                        if attempt == 3:
                            break
                        continue
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ {self.config.name}: Article timeout after {timeout_seconds}s (attempt {attempt})")
                    if attempt == 3:
                        break
                    continue
                    
            logger.error(f"❌ {self.config.name}: Failed to extract {url} after all attempts")
            return None
                
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Error extracting article from {url}: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """Check health using the SINGLE global browser."""
        try:
            # Get the SINGLE global browser (shared by all sources)
            crawler = await _single_browser_pool.get_global_browser()
            
            logger.debug(f"{self.config.name}: Running health check with SINGLE browser")
            
            test_result = await asyncio.wait_for(
                crawler.arun(
                    url="https://httpbin.org/html",
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                ),
                timeout=15
            )
            
            is_healthy = test_result.success
            logger.debug(f"{self.config.name}: Health check {'passed' if is_healthy else 'failed'}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"{self.config.name}: Health check failed: {str(e)}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.crawler:
            await self.crawler.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    def __del__(self):
        """Clean up crawler resources."""
        if self.crawler:
            try:
                asyncio.create_task(self.crawler.aclose())
            except:
                pass
            try:
                asyncio.create_task(self.crawler.aclose())
            except:
                pass

# Backward compatibility - provide the old class name as an alias
Crawl4AIExtractor = EnhancedCrawl4AIExtractor
