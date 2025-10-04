# crawler/models/__init__.py
"""
Data models for NewsRagnarok Crawler.
Contains domain models following Domain-Driven Design principles.
"""

from .source_models import (
    ProcessingStatus,
    ContentMetrics,
    ProcessingJob,
    SourceHealth,
    CrawlerConfig,
    TemplateConfig
)

from .article_models import (
    ArticleContent,
    ArticleStats
)

__all__ = [
    # Source models
    'ProcessingStatus',
    'ContentMetrics', 
    'ProcessingJob',
    'SourceHealth',
    'CrawlerConfig',
    'TemplateConfig',
    
    # Article models
    'ArticleContent',
    'ArticleStats'
]
