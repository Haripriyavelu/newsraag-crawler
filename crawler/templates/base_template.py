# crawler/templates/base_template.py
"""
Base template implementing common functionality for all source types.
Follows Template Method Pattern and provides extension points.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any
import asyncio
import time
from datetime import datetime

from crawler.interfaces.news_source_interface import (
    INewsSource, IArticleDiscovery, IContentExtractor, 
    IContentProcessor, IDuplicateChecker, IContentStorage,
    SourceConfig, ArticleMetadata, ProcessingResult,
    NewsSourceError, SourceDiscoveryError
)
from crawler.models.source_models import ProcessingJob, ProcessingStatus, ContentMetrics


class BaseNewsSourceTemplate(INewsSource):
    """
    Base template for all news sources.
    Implements Template Method pattern with extension points.
    """
    
    def __init__(self, source_config: SourceConfig):
        """Initialize with source configuration."""
        self._config = source_config
        self._initialize_services()
        
        print(f"Initialized news source: {self.config.name} ({self.config.source_type.value})")
    
    @property
    def config(self) -> SourceConfig:
        """Get source configuration."""
        return self._config
    
    def _initialize_services(self):
        """Initialize service dependencies. Override in subclasses if needed."""
        self._discovery_service = self._create_discovery_service()
        self._extractor_service = self._create_extractor_service()
        self._processor_service = self._create_processor_service()
        self._duplicate_checker = self._create_duplicate_checker()
        self._storage_service = self._create_storage_service()
    
    # Abstract methods for service creation (Factory methods)
    @abstractmethod
    def _create_discovery_service(self) -> IArticleDiscovery:
        """Create article discovery service."""
        pass
    
    @abstractmethod
    def _create_extractor_service(self) -> IContentExtractor:
        """Create content extraction service."""
        pass
    
    @abstractmethod
    def _create_processor_service(self) -> IContentProcessor:
        """Create content processing service."""
        pass
    
    @abstractmethod
    def _create_duplicate_checker(self) -> IDuplicateChecker:
        """Create duplicate checking service."""
        pass
    
    @abstractmethod
    def _create_storage_service(self) -> IContentStorage:
        """Create storage service."""
        pass
    
    # Interface implementations
    def get_discovery_service(self) -> IArticleDiscovery:
        """Get article discovery service."""
        return self._discovery_service
    
    def get_extractor_service(self) -> IContentExtractor:
        """Get content extraction service."""
        return self._extractor_service
    
    def get_processor_service(self) -> IContentProcessor:
        """Get content processing service."""
        return self._processor_service
    
    def get_duplicate_checker(self) -> IDuplicateChecker:
        """Get duplicate checking service."""
        return self._duplicate_checker
    
    def get_storage_service(self) -> IContentStorage:
        """Get storage service."""
        return self._storage_service
    
    async def health_check(self) -> bool:
        """Check if source is healthy and accessible."""
        try:
            # Template method - can be overridden
            return await self._perform_health_check()
        except Exception as e:
            print(f"Health check failed for {self.config.name}: {e}")
            return False
    
    async def _perform_health_check(self) -> bool:
        """Default health check implementation."""
        try:
            # Try to discover one article to test connectivity
            discovery_service = self.get_discovery_service()
            async for article in discovery_service.discover_articles():
                # If we can get at least one article, source is healthy
                return True
            return False
        except Exception:
            return False
    
    # Template method for processing articles
    async def process_articles(self) -> Dict[str, Any]:
        """
        Main template method for processing articles from source.
        This is the orchestration method that uses all services.
        """
        start_time = time.time()
        stats = {
            'source_name': self.config.name,
            'articles_discovered': 0,
            'articles_processed': 0,
            'articles_failed': 0,
            'articles_skipped': 0,
            'processing_time': 0,
            'errors': []
        }
        
        try:
            print(f"Starting article processing for {self.config.name}")
            
            # Rate limiting setup
            last_request_time = 0
            
            # Get services
            discovery_service = self.get_discovery_service()
            extractor_service = self.get_extractor_service()
            processor_service = self.get_processor_service()
            duplicate_checker = self.get_duplicate_checker()
            storage_service = self.get_storage_service()
            
            articles_processed = 0
            max_articles = self.config.max_articles_per_run
            
            async for article_meta in discovery_service.discover_articles():
                if articles_processed >= max_articles:
                    print(f"Reached max articles limit ({max_articles}) for {self.config.name}")
                    break
                
                stats['articles_discovered'] += 1
                
                try:
                    # Rate limiting
                    current_time = time.time()
                    time_since_last = current_time - last_request_time
                    if time_since_last < self.config.rate_limit_seconds:
                        sleep_time = self.config.rate_limit_seconds - time_since_last
                        await asyncio.sleep(sleep_time)
                    
                    last_request_time = time.time()
                    
                    # Check for duplicates
                    if await duplicate_checker.is_duplicate(article_meta):
                        print(f"Skipping duplicate article: {article_meta.title[:50]}...")
                        stats['articles_skipped'] += 1
                        continue
                    
                    # Extract content
                    extraction_result = await extractor_service.extract_content(article_meta)
                    if not extraction_result.success:
                        raise NewsSourceError(f"Content extraction failed: {extraction_result.error}")
                    
                    # Process content
                    processing_result = await processor_service.process_content(
                        extraction_result.content, article_meta
                    )
                    if not processing_result.success:
                        raise NewsSourceError(f"Content processing failed: {processing_result.error}")
                    
                    # Store content
                    storage_success = await storage_service.store_content(
                        processing_result.content, article_meta
                    )
                    if not storage_success:
                        raise NewsSourceError("Content storage failed")
                    
                    stats['articles_processed'] += 1
                    articles_processed += 1
                    
                    print(f"Successfully processed: {article_meta.title[:50]}...")
                    
                except Exception as e:
                    stats['articles_failed'] += 1
                    stats['errors'].append(str(e))
                    print(f"Failed to process article {article_meta.title[:50]}...: {e}")
            
            # Calculate final stats
            stats['processing_time'] = time.time() - start_time
            success_rate = (stats['articles_processed'] / max(1, stats['articles_discovered'])) * 100
            
            print(
                f"Completed processing for {self.config.name}: "
                f"{stats['articles_processed']}/{stats['articles_discovered']} articles processed "
                f"({success_rate:.1f}% success rate) in {stats['processing_time']:.2f}s"
            )
            
            return stats
            
        except Exception as e:
            stats['processing_time'] = time.time() - start_time
            stats['errors'].append(str(e))
            print(f"Critical error processing {self.config.name}: {e}")
            raise SourceDiscoveryError(f"Failed to process articles: {e}", self.config.name)



# Base service implementations that can be reused

class BaseArticleDiscovery(IArticleDiscovery, ABC):
    """Base implementation for article discovery."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
    
    @abstractmethod
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles - must be implemented by subclasses."""
        pass


class BaseContentExtractor(IContentExtractor, ABC):
    """Base implementation for content extraction."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
    
    @abstractmethod
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content - must be implemented by subclasses."""
        pass


class BaseContentProcessor(IContentProcessor):
    """Base implementation for content processing using LLM."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_llm_cleaner()
    
    def _initialize_llm_cleaner(self):
        """Initialize LLM cleaner if enabled."""
        try:
            from utils.llm.cleaner import create_llm_cleaner
            self.llm_cleaner = create_llm_cleaner()
            self.llm_enabled = True
            print("LLM cleaner initialized successfully")
        except Exception as e:
            print(f"LLM cleaner initialization failed: {e}")
            self.llm_cleaner = None
            self.llm_enabled = False
    
    async def process_content(self, content: str, metadata: ArticleMetadata) -> ProcessingResult:
        """Process content using LLM cleaning if available."""
        try:
            start_time = time.time()
            
            if self.llm_enabled and self.llm_cleaner:
                # Use LLM cleaning
                cleaned_content = await self._clean_with_llm(content, metadata)
                processing_time = time.time() - start_time
                
                return ProcessingResult(
                    success=True,
                    content=cleaned_content,
                    metadata={
                        'processing_method': 'llm_cleaning',
                        'processing_time': processing_time,
                        'original_length': len(content),
                        'processed_length': len(cleaned_content)
                    }
                )
            else:
                # Fallback to basic cleaning
                cleaned_content = self._basic_content_cleaning(content)
                processing_time = time.time() - start_time
                
                return ProcessingResult(
                    success=True,
                    content=cleaned_content,
                    metadata={
                        'processing_method': 'basic_cleaning',
                        'processing_time': processing_time,
                        'original_length': len(content),
                        'processed_length': len(cleaned_content)
                    }
                )
                
        except Exception as e:
            print(f"Content processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    async def _clean_with_llm(self, content: str, metadata: ArticleMetadata) -> str:
        """Clean content using LLM."""
        if not self.llm_cleaner:
            raise ValueError("LLM cleaner not available")
        
        # FIXED: Add the missing URL parameter
        result = await self.llm_cleaner.clean_content(content, metadata.source_name, metadata.url)
        
        # Handle tuple return (content, metadata) or direct string  
        if isinstance(result, tuple) and len(result) >= 2:
            return result[0]  # Return just the content
        elif isinstance(result, str):
            return result
        else:
            return content  # Fallback to original content
            
            # Use existing LLM cleaner
            return await self.llm_cleaner.clean_content(content, metadata.source_name)
    
    def _basic_content_cleaning(self, content: str) -> str:
        """Basic content cleaning without LLM."""
        import re
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove common boilerplate
        content = re.sub(r'Subscribe to.*?newsletter', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Follow us on.*?social', '', content, flags=re.IGNORECASE)
        
        return content.strip()


class BaseDuplicateChecker(IDuplicateChecker):
    """Base implementation for duplicate checking."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        try:
            from monitoring.duplicate_detector import get_duplicate_detector
            self.duplicate_detector = get_duplicate_detector()
        except ImportError:
            print("Warning: duplicate_detector not available, using basic check")
            self.duplicate_detector = None
    
    async def is_duplicate(self, article_meta: ArticleMetadata) -> bool:
        """Check if article is duplicate using existing duplicate detector."""
        try:
            if self.duplicate_detector:
                # Create article_data dict for the is_duplicate method
                article_data = {
                    'url': article_meta.url,
                    'title': article_meta.title
                }
                is_dup, _ = self.duplicate_detector.is_duplicate(article_data)
                return is_dup
            else:
                # Basic duplicate check - assume not duplicate
                return False
        except Exception as e:
            print(f"Duplicate check failed: {e}")
            return False  # Assume not duplicate if check fails



class BaseContentStorage(IContentStorage):
    """Base implementation for content storage."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_storage_clients()
    
    def _initialize_storage_clients(self):
        """Initialize storage clients."""
        try:
            from clients.vector_client import VectorClient
            self.vector_client = VectorClient()
            print("Vector storage client initialized")
        except Exception as e:
            print(f"Failed to initialize vector client: {e}")
            self.vector_client = None
    
    async def store_content(self, content: str, metadata: ArticleMetadata) -> bool:
        """Store content to vector database and blob storage."""
        try:
            if not self.vector_client:
                print("Vector client not available")
                return False
            
            # Create output model (reuse existing structure)
            from models.output import OutputModel
            output = OutputModel(
                title=metadata.title,
                publishDate=metadata.published_date,  # Required field - use datetime object
                content=content,  # Required field - use the extracted content
                url=metadata.url,
                source=metadata.source_name,
                author=metadata.author,
                category=metadata.category,
                article_id=metadata.article_id  # Optional field - maps correctly
            )
            
            # Store in vector database
            # Prepare metadata for vector storage  
            doc_metadata = {
                "title": metadata.title,
                "source": metadata.source_name,
                "author": metadata.author,
                "category": metadata.category,
                "publishDate": metadata.published_date.isoformat() if metadata.published_date else None,
                "article_id": metadata.article_id
            }
            
            # Use add_document method with content string and metadata dict
            result = await self.vector_client.add_document(content, doc_metadata)
            
            if result and result.get('status') == 'success':
                print(f"Successfully stored article: {metadata.title[:50]}...")
                return True
            else:
                print(f"Failed to store article: {metadata.title[:50]}...")
                return False
            return success
            
        except Exception as e:
            print(f"Storage failed for article {metadata.title[:50]}...: {e}")
            return False
