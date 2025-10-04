# crawler/interfaces/news_source_interface.py
"""
Core interfaces for the news crawler system following best LLD practices.
Implements Interface Segregation Principle and Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import asyncio


class SourceType(Enum):
    """Enumeration of supported source types."""
    RSS = "rss"
    HTML_SCRAPING = "html_scraping"
    API = "api"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    REDDIT = "reddit"


class ContentType(Enum):
    """Enumeration of content categories."""
    FINANCIAL_NEWS = "financial_news"
    FOREX = "forex"
    STOCKS = "stocks"
    CRYPTO = "crypto"
    GENERAL_NEWS = "general_news"
    EDUCATIONAL = "educational"

@dataclass(frozen=True)
class ArticleMetadata:
    """Immutable article metadata following value object pattern."""
    title: str
    url: str
    published_date: datetime
    source_name: str
    article_id: str
    author: Optional[str] = None
    category: Optional[str] = None
    language: str = "en"
    tags: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.title.strip():
            raise ValueError("Title cannot be empty")
        if not self.url.strip():
            raise ValueError("URL cannot be empty")


@dataclass
class SourceConfig:
    """Configuration for news sources."""
    name: str
    source_type: SourceType
    content_type: ContentType
    base_url: str
    enabled: bool = True
    rss_url: Optional[str] = None
    selectors: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    rate_limit_seconds: int = 1
    requires_translation: bool = False
    custom_processing: bool = False
    max_articles_per_run: int = 50
    timeout_seconds: int = 30
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.name.strip():
            raise ValueError("Source name cannot be empty")
        if self.rate_limit_seconds < 0:
            raise ValueError("Rate limit must be non-negative")


class ProcessingResult:
    """Result of content processing operation."""
    
    def __init__(self, success: bool, content: Optional[str] = None, 
                 error: Optional[str] = None, metadata: Optional[Dict] = None):
        self.success = success
        self.content = content
        self.error = error
        self.metadata = metadata or {}
        self.processed_at = datetime.utcnow()


# Interface Segregation - Split into smaller, focused interfaces

class IArticleDiscovery(ABC):
    """Interface for discovering articles from a source."""
    
    @abstractmethod
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """
        Discover new articles from the source.
        
        Returns:
            AsyncGenerator of ArticleMetadata objects
            
        Raises:
            SourceDiscoveryError: When discovery fails
        """
        pass


class IContentExtractor(ABC):
    """Interface for extracting content from articles."""
    
    @abstractmethod
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """
        Extract full content from article URL.
        
        Args:
            article_meta: Metadata of article to extract
            
        Returns:
            ProcessingResult with extracted content or error
        """
        pass


class IContentProcessor(ABC):
    """Interface for processing extracted content."""
    
    @abstractmethod
    async def process_content(self, content: str, metadata: ArticleMetadata) -> ProcessingResult:
        """
        Process and clean extracted content.
        
        Args:
            content: Raw extracted content
            metadata: Article metadata for context
            
        Returns:
            ProcessingResult with processed content or error
        """
        pass


class IDuplicateChecker(ABC):
    """Interface for checking duplicate articles."""
    
    @abstractmethod
    async def is_duplicate(self, article_meta: ArticleMetadata) -> bool:
        """
        Check if article already exists in storage.
        
        Args:
            article_meta: Article metadata to check
            
        Returns:
            True if duplicate exists, False otherwise
        """
        pass


class IContentStorage(ABC):
    """Interface for storing processed content."""
    
    @abstractmethod
    async def store_content(self, content: str, metadata: ArticleMetadata) -> bool:
        """
        Store processed content to vector database and blob storage.
        
        Args:
            content: Processed content to store
            metadata: Article metadata
            
        Returns:
            True if storage successful, False otherwise
        """
        pass


class INewsSource(ABC):
    """
    Main interface for news sources. Composition of other interfaces.
    Follows Single Responsibility and Interface Segregation principles.
    """
    
    @property
    @abstractmethod
    def config(self) -> SourceConfig:
        """Get source configuration."""
        pass
    
    @abstractmethod
    def get_discovery_service(self) -> IArticleDiscovery:
        """Get article discovery service."""
        pass
    
    @abstractmethod
    def get_extractor_service(self) -> IContentExtractor:
        """Get content extraction service."""
        pass
    
    @abstractmethod
    def get_processor_service(self) -> IContentProcessor:
        """Get content processing service."""
        pass
    
    @abstractmethod
    def get_duplicate_checker(self) -> IDuplicateChecker:
        """Get duplicate checking service."""
        pass
    
    @abstractmethod
    def get_storage_service(self) -> IContentStorage:
        """Get storage service."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is healthy and accessible."""
        pass


# Custom Exceptions following best practices

class NewsSourceError(Exception):
    """Base exception for news source operations."""
    
    def __init__(self, message: str, source_name: str = "", cause: Optional[Exception] = None):
        super().__init__(message)
        self.source_name = source_name
        self.cause = cause


class SourceDiscoveryError(NewsSourceError):
    """Exception raised during article discovery."""
    pass


class ContentExtractionError(NewsSourceError):
    """Exception raised during content extraction."""
    pass


class ContentProcessingError(NewsSourceError):
    """Exception raised during content processing."""
    pass


class StorageError(NewsSourceError):
    """Exception raised during content storage."""
    pass
