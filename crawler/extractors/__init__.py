"""
Backward compatibility wrapper for the old Crawl4AIExtractor.
This ensures any code still importing the old class will use the enhanced version.
"""

# Import the enhanced version as the default
from .crawl4ai_extractor import EnhancedCrawl4AIExtractor

# Provide backward compatibility
class Crawl4AIExtractor(EnhancedCrawl4AIExtractor):
    """
    Backward compatibility wrapper for the old Crawl4AIExtractor.
    
    This class inherits from EnhancedCrawl4AIExtractor to ensure all existing
    code that imports Crawl4AIExtractor automatically gets the enhanced timeout
    handling and better error recovery.
    """
    
    def __init__(self, config):
        super().__init__(config)
        # Log that the enhanced version is being used
        from loguru import logger
        logger.debug(f"🔧 Using enhanced Crawl4AI extractor for {config.name} (backward compatibility)")

# For direct imports
__all__ = ['Crawl4AIExtractor', 'EnhancedCrawl4AIExtractor']
