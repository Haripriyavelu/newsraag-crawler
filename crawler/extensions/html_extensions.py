"""
Source factory extension - follows Open-Closed Principle.
Extends source creation without modifying base factory.
"""

from ..factories.source_factory import SourceFactory
from ..templates.rss_template import RSSNewsSourceTemplate
from ..extensions.enhanced_extractor import EnhancedContentExtractor
from ..interfaces.news_source_interface import SourceConfig


class ExtendedRSSTemplate(RSSNewsSourceTemplate):
    """Extended RSS template with HTML extraction capability."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        
        # Replace content extractor with enhanced version (Dependency Injection)
        if hasattr(self, '_content_extractor'):
            self._content_extractor = EnhancedContentExtractor(config)


# Register extension with factory
def register_html_extensions():
    """Register HTML scraping extensions with the factory."""
    
    # For Kabutan - inject enhanced extractor
    def create_kabutan_source(config: SourceConfig):
        config.content_extraction = 'html'  # Enable HTML extraction
        config.selectors = {'content': '.news-body, .article-body, .news-content'}
        return ExtendedRSSTemplate(config)
    
    # For PoundSterlingLive - inject enhanced extractor  
    def create_psl_source(config: SourceConfig):
        config.content_extraction = 'html'  # Enable HTML extraction
        config.selectors = {'content': '.entry-content, .post-content, .article-content'}
        return ExtendedRSSTemplate(config)
    
    # Register with existing factory (Extension, not Modification)
    SourceFactory._CUSTOM_ADAPTERS['kabutan'] = create_kabutan_source
    SourceFactory._CUSTOM_ADAPTERS['poundsterlinglive'] = create_psl_source


# Auto-register when module is imported
register_html_extensions()
