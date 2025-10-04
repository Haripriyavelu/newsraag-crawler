# crawler/factories/config_loader.py
"""
Enhanced configuration loader for the new template system.
Loads sources from YAML and converts to new SourceConfig format.
"""
from typing import List, Dict, Any, Optional

from crawler.interfaces.news_source_interface import SourceConfig, SourceType, ContentType
from crawler.validators import ConfigValidator


class EnhancedConfigLoader:
    """Enhanced configuration loader for new template system."""
    
    @classmethod
    def load_from_yaml(cls, config_path: str) -> List[SourceConfig]:
        """
        Load source configurations from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            List of SourceConfig objects
        """
        try:
            # Try to import yaml
            try:
                import yaml
            except ImportError:
                print("Warning: PyYAML not available, cannot load YAML config")
                return []
            
            with open(config_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            if not data or 'sources' not in data:
                print(f"No sources found in {config_path}")
                return []
            
            configs = []
            for source_data in data['sources']:
                try:
                    config = cls._convert_yaml_to_config(source_data)
                    if config:
                        configs.append(config)
                except Exception as e:
                    print(f"Failed to process source config: {e}")
                    continue
            
            print(f"Loaded {len(configs)} source configurations from {config_path}")
            return configs
            
        except Exception as e:
            print(f"Failed to load configuration from {config_path}: {e}")
            return []
    
    @classmethod
    def _convert_yaml_to_config(cls, source_data: Dict[str, Any]) -> Optional[SourceConfig]:
        """Convert YAML source data to SourceConfig."""
        try:
            # Required fields
            name = source_data.get('name')
            source_type_str = source_data.get('type')
            url = source_data.get('url')
            
            if not all([name, source_type_str, url]):
                print(f"Missing required fields for source: {source_data}")
                return None
            
            # Map source type
            source_type = cls._map_source_type(source_type_str)
            
            # Determine content type based on source name/type
            content_type = cls._determine_content_type(name, source_data)
            
            # Create SourceConfig
            config = SourceConfig(
                name=name,
                source_type=source_type,
                content_type=content_type,
                base_url=cls._extract_base_url(url),
                rss_url=url if source_type == SourceType.RSS else None,
                enabled=source_data.get('enabled', True),
                rate_limit_seconds=source_data.get('rate_limit', 1),
                max_articles_per_run=source_data.get('max_articles', 50),
                timeout_seconds=source_data.get('timeout', 30),
                requires_translation=source_data.get('translate', False),
                custom_processing=True,  # All existing sources use custom processing
                headers=source_data.get('headers'),
                selectors=source_data.get('selectors')
            )
            
            # Validate configuration
            errors = ConfigValidator.validate_source_config(config)
            if errors:
                print(f"Configuration errors for {name}: {errors}")
                # Return config anyway for now (non-blocking validation)
            
            return config
            
        except Exception as e:
            print(f"Failed to convert source data: {e}")
            return None
    
    @classmethod
    def _map_source_type(cls, type_str: str) -> SourceType:
        """Map string source type to SourceType enum."""
        type_mapping = {
            'rss': SourceType.RSS,
            'html': SourceType.HTML_SCRAPING,
            'html_scraping': SourceType.HTML_SCRAPING,  # Support both formats
            'api': SourceType.API,
            'youtube': SourceType.YOUTUBE,
        }
        return type_mapping.get(type_str.lower(), SourceType.RSS)
    
    @classmethod
    def _determine_content_type(cls, name: str, source_data: Dict[str, Any]) -> ContentType:
        """Determine content type based on source name and data."""
        # Source-specific mapping
        source_content_mapping = {
            'babypips': ContentType.FOREX,
            'fxstreet': ContentType.FOREX,
            'forexlive': ContentType.FOREX,
            'kabutan': ContentType.STOCKS,
            'poundsterlinglive': ContentType.FOREX,
        }
        
        # Check if explicit content type specified
        if 'content_type' in source_data:
            content_type_str = source_data['content_type'].lower()
            content_type_mapping = {
                'forex': ContentType.FOREX,
                'stocks': ContentType.STOCKS,
                'crypto': ContentType.CRYPTO,
                'financial_news': ContentType.FINANCIAL_NEWS,
                'news': ContentType.GENERAL_NEWS,
                'education': ContentType.EDUCATIONAL,
            }
            return content_type_mapping.get(content_type_str, ContentType.FINANCIAL_NEWS)
        
        # Use source-specific mapping
        return source_content_mapping.get(name.lower(), ContentType.FINANCIAL_NEWS)
    
    @classmethod
    def _extract_base_url(cls, url: str) -> str:
        """Extract base URL from full URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return url


# Convenience functions
def load_sources_from_yaml(config_path: str) -> List[SourceConfig]:
    """Convenience function to load sources from YAML."""
    return EnhancedConfigLoader.load_from_yaml(config_path)

def create_sources_from_yaml(config_path: str) -> Dict[str, Any]:
    """Load sources from YAML and create source instances."""
    from crawler.factories.source_factory import SourceFactory
    
    configs = load_sources_from_yaml(config_path)
    if not configs:
        return {}
    
    return SourceFactory.create_sources_from_config_list(configs)
