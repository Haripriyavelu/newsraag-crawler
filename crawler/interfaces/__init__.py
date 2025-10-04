# crawler/interfaces/__init__.py
"""
Interfaces package for NewsRagnarok Crawler.
Contains all interface definitions following SOLID principles.
"""

from .news_source_interface import (
    # Core interfaces
    INewsSource,
    IArticleDiscovery,
    IContentExtractor,
    IContentProcessor,
    IDuplicateChecker,
    IContentStorage,
    
    # Data models
    SourceConfig,
    ArticleMetadata,
    ProcessingResult,
    
    # Enums
    SourceType,
    ContentType,
    
    # Exceptions
    NewsSourceError,
    SourceDiscoveryError,
    ContentExtractionError,
    ContentProcessingError,
    StorageError
)

__all__ = [
    # Core interfaces
    'INewsSource',
    'IArticleDiscovery', 
    'IContentExtractor',
    'IContentProcessor',
    'IDuplicateChecker',
    'IContentStorage',
    
    # Data models
    'SourceConfig',
    'ArticleMetadata', 
    'ProcessingResult',
    
    # Enums
    'SourceType',
    'ContentType',
    
    # Exceptions
    'NewsSourceError',
    'SourceDiscoveryError',
    'ContentExtractionError', 
    'ContentProcessingError',
    'StorageError'
]
