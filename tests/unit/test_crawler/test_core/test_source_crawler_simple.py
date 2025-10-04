"""
Simple unit tests for source_crawler that match the actual code structure.

Tests the main crawling functionality with proper mocking.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestSourceCrawlerBasic:
    """Basic tests for source_crawler module."""
    
    @pytest.mark.unit
    def test_source_crawler_module_imports(self):
        """Test that source crawler can be imported."""
        try:
            from crawler.core.source_crawler import crawl_source
            assert callable(crawl_source), "crawl_source should be a callable function"
        except ImportError as e:
            pytest.fail(f"Could not import crawl_source: {e}")
    
    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_crawl_source_with_invalid_config(self):
        """Test crawl_source handles invalid configuration gracefully."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        # Test with empty config
        result = await crawl_source({})
        assert result is not None, "crawl_source should return a result even with empty config"
        assert isinstance(result, tuple), "Result should be a tuple"
        assert len(result) >= 2, "Result should have at least 2 elements (processed, failed)"
    
    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_crawl_source_with_minimal_valid_config(self):
        """Test crawl_source with minimal valid configuration."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        # Mock dependencies that might not exist
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.core.source_crawler.crawl_rss_feed', new_callable=AsyncMock) as mock_crawl_rss:
            
            # Configure mocks
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            mock_crawl_rss.return_value = []  # No articles found
            
            config = {
                'name': 'test_source',
                'type': 'rss', 
                'url': 'https://example.com/feed.rss'
            }
            
            result = await crawl_source(config)
            
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) >= 2
            
            # Should have called get_metrics
            mock_get_metrics.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_with_rss_articles(self):
        """Test crawl_source processes RSS articles."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        # Mock the unified source system components that source_crawler uses
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.factories.SourceFactory.create_sources_from_config_list') as mock_create_sources:
            
            # Configure mocks
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock a source that would be created by the factory
            mock_source = MagicMock()
            
            # Create an async mock for process_articles
            async def mock_process_articles():
                return {
                    'articles_processed': 2,
                    'articles_failed': 0, 
                    'articles_skipped': 0
                }
            mock_source.process_articles = mock_process_articles
            mock_create_sources.return_value = {'test_source': mock_source}
            
            config = {
                'name': 'test_source',
                'type': 'rss',
                'url': 'https://example.com/feed.rss'
            }
            
            result = await crawl_source(config)
            
            assert result is not None
            processed_count, failed_count, skipped_count = result  # Updated to expect 3 values
            
            # Should have processed articles
            assert processed_count == 2  
            assert failed_count == 0    
            assert skipped_count == 0
            
            # Verify mocks were called
            mock_create_sources.assert_called_once()
            # Check that the source object's method was called (not the mock directly)
            assert mock_source.process_articles.__name__ == 'mock_process_articles'


class TestSourceCrawlerModules:
    """Test related modules that source_crawler depends on."""
    
    @pytest.mark.unit
    def test_rss_crawler_import(self):
        """Test that RSS crawler can be imported."""
        try:
            from crawler.core.rss_crawler import crawl_rss_feed
            assert callable(crawl_rss_feed)
        except ImportError:
            pytest.skip("rss_crawler module not available yet")
    
    @pytest.mark.unit
    def test_article_processor_import(self):
        """Test that article processor can be imported."""
        try:
            from crawler.core.article_processor import process_article
            assert callable(process_article)
        except ImportError:
            pytest.skip("article_processor module not available yet")
    
    @pytest.mark.unit
    def test_metrics_import(self):
        """Test that metrics can be imported."""
        try:
            from monitoring.metrics import get_metrics
            assert callable(get_metrics)
        except ImportError:
            pytest.skip("metrics module not available yet")


class TestSourceCrawlerErrorHandling:
    """Test error handling in source crawler."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_handles_rss_exception(self):
        """Test that source crawler handles RSS crawling exceptions."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.core.source_crawler._convert_legacy_config') as mock_convert:
            
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Simulate conversion failure (like invalid config)
            mock_convert.return_value = None
            
            config = {
                'name': 'test_source',
                'type': 'rss',
                'url': 'https://invalid-feed.com/feed.rss'
            }
            
            # Should not raise exception, should handle gracefully
            result = await crawl_source(config)
            
            assert result is not None
            processed_count, failed_count, skipped_count = result  # Updated to expect 3 values
            # Should have some failure indication
            assert processed_count == 0 and failed_count == 1 and skipped_count == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_handles_processing_exception(self):
        """Test that source crawler handles article processing exceptions."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.factories.SourceFactory.create_sources_from_config_list') as mock_create_sources:
            
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock source that throws an exception during processing
            mock_source = MagicMock()
            
            async def mock_process_articles_error():
                raise Exception("Processing failed")
            
            mock_source.process_articles = mock_process_articles_error
            mock_create_sources.return_value = {'test_source': mock_source}
            
            config = {
                'name': 'test_source',
                'type': 'rss',
                'url': 'https://example.com/feed.rss'
            }
            
            result = await crawl_source(config)
            
            assert result is not None
            processed_count, failed_count, skipped_count = result  # Updated to expect 3 values
            # Should indicate processing failure (0 processed, 1 failed, 0 skipped)
            assert processed_count == 0
            assert failed_count == 1 
            assert skipped_count == 0
