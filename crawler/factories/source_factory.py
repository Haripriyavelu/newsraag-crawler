# crawler/factories/source_factory.py
"""
Factory for creating news sources based on configuration.
Implements Factory Pattern with template system for unified source management.
"""
from typing import Dict, Type, Optional, Any, List

from crawler.interfaces.news_source_interface import (
    INewsSource, SourceConfig, SourceType, NewsSourceError
)
from crawler.templates.rss_template import RSSNewsSourceTemplate
from crawler.templates.universal_template import UniversalTemplate
from crawler.templates.hierarchical_template import HierarchicalTemplate


class SourceFactory:
    """
    Factory for creating news source implementations.
    Supports template-based source creation through YAML configuration.
    """
    
    # Registry of template classes for each source type
    _TEMPLATE_REGISTRY: Dict[SourceType, Type[INewsSource]] = {
        SourceType.RSS: lambda config: HierarchicalTemplate(config),  # Use hierarchical for RSS
        SourceType.HTML_SCRAPING: lambda config: HierarchicalTemplate(config),  # Use hierarchical for HTML scraping
        SourceType.YOUTUBE: lambda config: UniversalTemplate(config),
        SourceType.TWITTER: lambda config: UniversalTemplate(config), 
        SourceType.REDDIT: lambda config: UniversalTemplate(config),
        # Add new source types here - Open-Closed Principle!
    }
    
    # Custom adapters are deprecated - templates handle everything via YAML
    _CUSTOM_ADAPTERS: Dict[str, Type[INewsSource]] = {}
    
    @classmethod
    def create_source(cls, config: SourceConfig) -> INewsSource:
        """
        Create a news source implementation based on configuration.
        
        Args:
            config: Source configuration
            
        Returns:
            INewsSource implementation
            
        Raises:
            NewsSourceError: If source cannot be created
        """
        try:
            print(f"Creating news source: {config.name} ({config.source_type.value})")
            
            # Validate configuration
            cls._validate_config(config)
            
            # Create template-based source (only strategy now)
            print(f"Using template-based implementation for {config.name}")
            return cls._create_template_source(config)
            
        except Exception as e:
            print(f"Failed to create source {config.name}: {e}")
            raise NewsSourceError(f"Source creation failed: {e}", config.name)
    
    @classmethod
    def _validate_config(cls, config: SourceConfig) -> None:
        """Validate source configuration."""
        if not config.name.strip():
            raise ValueError("Source name cannot be empty")
        
        # Source-type specific validation
        if config.source_type == SourceType.RSS and not config.rss_url:
            raise ValueError(f"RSS URL is required for RSS source: {config.name}")
        
        if config.source_type == SourceType.HTML_SCRAPING and not config.base_url:
            raise ValueError(f"Base URL is required for HTML scraping source: {config.name}")
        
        print(f"Configuration validated for {config.name}")
    
    @classmethod
    def _create_template_source(cls, config: SourceConfig) -> INewsSource:
        """Create template-based source implementation."""
        template_class = cls._TEMPLATE_REGISTRY.get(config.source_type)
        if not template_class:
            raise ValueError(f"No template available for source type: {config.source_type}")
        
        return template_class(config)
    
    @classmethod
    def register_template(cls, source_type: SourceType, template_class: Type[INewsSource]) -> None:
        """Register a new template class for a source type."""
        cls._TEMPLATE_REGISTRY[source_type] = template_class
        print(f"Registered template {template_class.__name__} for type {source_type.value}")
    
    @classmethod
    def get_supported_source_types(cls) -> List[SourceType]:
        """Get list of supported source types."""
        return list(cls._TEMPLATE_REGISTRY.keys())
    
    @classmethod
    def can_create_source(cls, config: SourceConfig) -> bool:
        """Check if factory can create source for given configuration."""
        try:
            cls._validate_config(config)
            # Check if we have a template for this source type
            return config.source_type in cls._TEMPLATE_REGISTRY
        except Exception:
            return False
    
    @classmethod
    def create_sources_from_config_list(cls, configs: List[SourceConfig]) -> Dict[str, INewsSource]:
        """
        Create multiple sources from configuration list.
        
        Args:
            configs: List of source configurations
            
        Returns:
            Dictionary mapping source names to INewsSource instances
        """
        sources = {}
        successful = 0
        failed = 0
        
        for config in configs:
            try:
                if not config.enabled:
                    print(f"Skipping disabled source: {config.name}")
                    continue
                
                source = cls.create_source(config)
                sources[config.name] = source
                successful += 1
                print(f"Successfully created source: {config.name}")
                
            except Exception as e:
                failed += 1
                print(f"Failed to create source {config.name}: {e}")
                # Continue with other sources
        
        print(f"Source creation summary: {successful} successful, {failed} failed")
        return sources
    
    @classmethod
    def get_creation_info(cls, source_name: str) -> Dict[str, Any]:
        """Get information about how a source would be created."""
        info = {
            'source_name': source_name,
            'has_custom_adapter': source_name in cls._CUSTOM_ADAPTERS,
            'adapter_class': cls._CUSTOM_ADAPTERS.get(source_name).__name__ if source_name in cls._CUSTOM_ADAPTERS else None,
            'supported_templates': [st.value for st in cls._TEMPLATE_REGISTRY.keys()],
            'creation_strategy': None
        }
        
        if source_name in cls._CUSTOM_ADAPTERS:
            info['creation_strategy'] = SourceCreationStrategy.CUSTOM_ADAPTER.value
        
        return info


# Convenience function for easy source creation
def create_source_from_config(config: SourceConfig) -> INewsSource:
    """Convenience function to create a source from configuration."""
    return SourceFactory.create_source(config)


# Helper function to create all your existing sources
def create_all_existing_sources() -> Dict[str, INewsSource]:
    """Create all 5 existing sources with their configurations."""
    from crawler.interfaces import ContentType
    
    configs = [
        # BabyPips (RSS)
        SourceConfig(
            name="babypips",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.babypips.com",
            rss_url="https://www.babypips.com/feed.rss",
            rate_limit_seconds=2,
            max_articles_per_run=50,
            custom_processing=True
        ),
        
        # FXStreet (RSS)
        SourceConfig(
            name="fxstreet",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.fxstreet.com",
            rss_url="https://www.fxstreet.com/rss/news",
            rate_limit_seconds=1,
            max_articles_per_run=50,
            custom_processing=True
        ),
        
        # ForexLive (RSS)
        SourceConfig(
            name="forexlive",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.forexlive.com",
            rss_url="https://www.forexlive.com/feed/",
            rate_limit_seconds=1,
            max_articles_per_run=50,
            custom_processing=True
        ),
        
        # Kabutan (HTML with translation)
        SourceConfig(
            name="kabutan",
            source_type=SourceType.HTML_SCRAPING,
            content_type=ContentType.STOCKS,
            base_url="https://kabutan.jp/news/marketnews/",
            rate_limit_seconds=2,
            max_articles_per_run=30,
            requires_translation=True,
            custom_processing=True
        ),
        
        # PoundSterlingLive (HTML)
        SourceConfig(
            name="poundsterlinglive",
            source_type=SourceType.HTML_SCRAPING,
            content_type=ContentType.FOREX,
            base_url="https://www.poundsterlinglive.com/markets",
            rate_limit_seconds=2,
            max_articles_per_run=40,
            custom_processing=True
        )
    ]
    
    return SourceFactory.create_sources_from_config_list(configs)
