"""
Universal template that works with all source types using the extractor registry.
This is Open-Closed: add new extractors to registry without modifying this class.
"""

from typing import Dict, Any
from ..templates.base_template import BaseNewsSourceTemplate
from ..interfaces.news_source_interface import (
    IArticleDiscovery, IContentExtractor, IContentProcessor, 
    IDuplicateChecker, IContentStorage, SourceConfig
)
from ..extractors.article_discovery import create_article_discovery
from ..extractors.content_extractors import create_content_extractor


class UniversalTemplate(BaseNewsSourceTemplate):
    """
    Universal template that handles all source types through registry pattern.
    Following Open-Closed Principle: extensible without modification.
    """
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        """Create discovery service based on source type."""
        config_dict = {
            'name': self.config.name,
            'url': self.config.base_url or self.config.rss_url,
            'selectors': getattr(self.config, 'selectors', {}),
        }
        return create_article_discovery(self.config.source_type.value, config_dict)
    
    def _create_extractor_service(self) -> IContentExtractor:
        """Create extractor service based on source type."""
        config_dict = {
            'name': self.config.name,
            'url': self.config.base_url or self.config.rss_url,
            'selectors': getattr(self.config, 'selectors', {}),
        }
        return create_content_extractor(self.config.source_type.value, config_dict)
    
    def _create_processor_service(self) -> IContentProcessor:
        """Create processor service - reuse existing implementation."""
        from ..templates.base_template import BaseContentProcessor
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self) -> IDuplicateChecker:
        """Create duplicate checker - reuse existing implementation."""
        from ..templates.base_template import BaseDuplicateChecker
        return BaseDuplicateChecker(self.config)  # FIX: Pass required config parameter  # FIX: Pass required config parameter
    
    def _create_storage_service(self) -> IContentStorage:
        """Create storage service - reuse existing implementation."""
        from ..templates.base_template import BaseContentStorage
        return BaseContentStorage(self.config)  # FIX: Pass required config parameter


# Factory function for the source factory
def create_universal_source(config: SourceConfig):
    """Create universal source that works with any type."""
    return UniversalTemplate(config)
