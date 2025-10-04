# crawler/validators/config_validator.py
"""
Configuration validation utilities.
"""
from typing import List, Dict, Any
import re
from urllib.parse import urlparse

from crawler.interfaces.news_source_interface import SourceConfig, SourceType


class ConfigValidator:
    """Validator for source configurations."""
    
    @classmethod
    def validate_source_config(cls, config: SourceConfig) -> List[str]:
        """
        Validate a source configuration.
        
        Args:
            config: SourceConfig to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Basic field validation
        errors.extend(cls._validate_basic_fields(config))
        
        # URL validation
        errors.extend(cls._validate_urls(config))
        
        # Type-specific validation
        errors.extend(cls._validate_source_type_requirements(config))
        
        # Numeric field validation
        errors.extend(cls._validate_numeric_fields(config))
        
        return errors
    
    @classmethod
    def _validate_basic_fields(cls, config: SourceConfig) -> List[str]:
        """Validate basic required fields."""
        errors = []
        
        if not config.name or not config.name.strip():
            errors.append("Source name cannot be empty")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', config.name):
            errors.append("Source name can only contain letters, numbers, underscores, and hyphens")
        
        if not config.base_url or not config.base_url.strip():
            errors.append("Base URL cannot be empty")
            
        return errors
    
    @classmethod
    def _validate_urls(cls, config: SourceConfig) -> List[str]:
        """Validate URL fields."""
        errors = []
        
        # Validate base URL
        if config.base_url:
            if not cls._is_valid_url(config.base_url):
                errors.append(f"Invalid base URL: {config.base_url}")
        
        # Validate RSS URL if provided
        if config.rss_url:
            if not cls._is_valid_url(config.rss_url):
                errors.append(f"Invalid RSS URL: {config.rss_url}")
                
        return errors
    
    @classmethod
    def _validate_source_type_requirements(cls, config: SourceConfig) -> List[str]:
        """Validate source type specific requirements."""
        errors = []
        
        if config.source_type == SourceType.RSS:
            if not config.rss_url:
                errors.append("RSS URL is required for RSS sources")
        
        elif config.source_type == SourceType.HTML_SCRAPING:
            if not config.selectors or not config.selectors.get('content'):
                errors.append("Content selector is required for HTML scraping sources")
        
        elif config.source_type == SourceType.API:
            if not config.headers or 'Authorization' not in config.headers:
                # API source may need authorization headers (warning only)
                pass
                
        return errors
    
    @classmethod
    def _validate_numeric_fields(cls, config: SourceConfig) -> List[str]:
        """Validate numeric fields."""
        errors = []
        
        if config.rate_limit_seconds < 0:
            errors.append("Rate limit seconds must be non-negative")
        
        if config.max_articles_per_run <= 0:
            errors.append("Max articles per run must be positive")
        
        if config.timeout_seconds <= 0:
            errors.append("Timeout seconds must be positive")
            
        return errors
    
    @classmethod
    def _is_valid_url(cls, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @classmethod
    def validate_config_dict(cls, config_dict: Dict[str, Any]) -> List[str]:
        """Validate configuration from dictionary format."""
        errors = []
        
        required_fields = ['name', 'type', 'base_url']
        for field in required_fields:
            if field not in config_dict:
                errors.append(f"Required field '{field}' is missing")
        
        # Check source type is valid
        if 'type' in config_dict:
            try:
                SourceType(config_dict['type'])
            except ValueError:
                valid_types = [t.value for t in SourceType]
                errors.append(f"Invalid source type '{config_dict['type']}'. Must be one of: {valid_types}")
        
        return errors
