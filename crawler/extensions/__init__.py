"""
Extensions package - follows Open-Closed Principle.
Provides extensions to base functionality without modifying core code.
"""

from .html_extensions import register_html_extensions
from .enhanced_extractor import EnhancedContentExtractor

# Auto-register extensions when package is imported
register_html_extensions()

__all__ = ['register_html_extensions', 'EnhancedContentExtractor']
