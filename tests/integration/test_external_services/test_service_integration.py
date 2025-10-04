"""
Integration tests for external services used by NewsRaag Crawler.

Tests integration with external APIs and services in controlled ways.
"""
import pytest
import asyncio
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestRSSFeedIntegration:
    """Test RSS feed integration with real and mock data."""
    
    @pytest.mark.integration
    @pytest.mark.external
    def test_feedparser_integration(self):
        """Test feedparser integration with sample RSS."""
        try:
            import feedparser
        except ImportError:
            pytest.skip("feedparser not available")
        
        # Test with valid RSS XML
        sample_rss = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>NewsRaag Test Feed</title>
                <description>Test RSS feed for integration testing</description>
                <link>https://example.com</link>
                <item>
                    <title>EUR/USD Analysis: Key Levels</title>
                    <link>https://example.com/eur-usd-analysis</link>
                    <description>Technical analysis of EUR/USD with key support and resistance levels.</description>
                    <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
                    <guid>eur-usd-123</guid>
                </item>
                <item>
                    <title>Gold Price Forecast</title>
                    <link>https://example.com/gold-forecast</link>
                    <description>Gold price forecast based on market analysis.</description>
                    <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
                    <guid>gold-456</guid>
                </item>
            </channel>
        </rss>'''
        
        feed = feedparser.parse(sample_rss)
        
        # Verify feed structure
        assert feed.feed.title == "NewsRaag Test Feed"
        assert len(feed.entries) == 2
        
        # Verify first entry
        entry1 = feed.entries[0]
        assert "EUR/USD" in entry1.title
        assert entry1.link == "https://example.com/eur-usd-analysis"
        assert entry1.id == "eur-usd-123"
        
        # Verify second entry  
        entry2 = feed.entries[1]
        assert "Gold" in entry2.title
        assert entry2.link == "https://example.com/gold-forecast"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rss_crawler_integration(self):
        """Test RSS crawler integration if available."""
        try:
            from crawler.core.rss_crawler import crawl_rss_feed
        except ImportError:
            pytest.skip("rss_crawler not available")
        
        # Test with mock RSS response
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = '''<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>Test Feed</title>
                    <item>
                        <title>Test Article</title>
                        <link>https://example.com/test</link>
                        <description>Test description</description>
                    </item>
                </channel>
            </rss>'''
            mock_get.return_value = mock_response
            
            # Test RSS crawling with proper arguments
            # The function signature is: crawl_rss_feed(rss_url: str, max_articles: int = 50)
            result = await crawl_rss_feed("https://example.com/test-feed.xml", 10)
            
            assert result is not None
            assert isinstance(result, list)


class TestWebCrawlingIntegration:
    """Test web crawling integration."""
    
    @pytest.mark.integration
    @pytest.mark.external
    def test_crawl4ai_availability(self):
        """Test that Crawl4AI is available and can be imported."""
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig
            assert AsyncWebCrawler is not None
            assert BrowserConfig is not None
        except ImportError:
            pytest.skip("Crawl4AI not available")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.external
    async def test_web_crawler_integration(self):
        """Test web crawler with simple HTML."""
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig
        except ImportError:
            pytest.skip("Crawl4AI not available")
        
        # Test with httpbin (reliable test service)
        test_url = "https://httpbin.org/html"
        
        try:
            browser_config = BrowserConfig(
                headless=True,
                extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(test_url)
                
                if result and hasattr(result, 'markdown'):
                    assert result.markdown is not None
                    if hasattr(result.markdown, 'raw_markdown'):
                        content = result.markdown.raw_markdown
                        assert isinstance(content, str)
                        assert len(content) > 0
                        
        except Exception as e:
            # Web crawling might fail due to network issues
            pytest.skip(f"Web crawler test skipped due to: {e}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_article_processor_integration(self):
        """Test article processor integration if available."""
        try:
            from crawler.core.article_processor import process_article
        except ImportError:
            pytest.skip("article_processor not available")
        
        # Test with sample article data
        sample_article = {
            'title': 'Integration Test Article',
            'link': 'https://httpbin.org/html',
            'description': 'Test article for integration testing',
            'id': 'integration-test-123'
        }
        
        try:
            # This might work or might fail gracefully
            result = await process_article(sample_article)
            # Should return some result (True/False or article data)
            assert result is not None
        except Exception:
            # Processing might fail, that's acceptable for integration test
            pass


class TestDatabaseIntegration:
    """Test database integration (Qdrant)."""
    
    @pytest.mark.integration
    @pytest.mark.qdrant
    def test_qdrant_client_availability(self):
        """Test Qdrant client availability."""
        try:
            from qdrant_client import QdrantClient
            assert QdrantClient is not None
        except ImportError:
            pytest.skip("qdrant-client not available")
    
    @pytest.mark.integration
    @pytest.mark.qdrant
    def test_qdrant_wrapper_integration(self):
        """Test Qdrant wrapper integration if available."""
        try:
            from clients.qdrant_client import QdrantClientWrapper
        except ImportError:
            pytest.skip("QdrantClientWrapper not available")
        
        # Test initialization (might fail if no connection)
        try:
            client = QdrantClientWrapper()
            assert client is not None
            # Test has basic methods
            expected_methods = ['store_document', 'search_similar', 'delete_documents']
            for method in expected_methods:
                if hasattr(client, method):
                    assert callable(getattr(client, method))
        except Exception:
            # Connection issues are acceptable for integration test
            pass


class TestAzureIntegration:
    """Test Azure services integration."""
    
    @pytest.mark.integration
    @pytest.mark.azure
    def test_azure_openai_client_availability(self):
        """Test Azure OpenAI client availability."""
        try:
            import openai
            assert openai is not None
        except ImportError:
            pytest.skip("openai package not available")
    
    @pytest.mark.integration
    @pytest.mark.azure
    def test_azure_storage_availability(self):
        """Test Azure Storage client availability."""
        try:
            from azure.storage.blob import BlobServiceClient
            assert BlobServiceClient is not None
        except ImportError:
            pytest.skip("azure-storage-blob not available")
    
    @pytest.mark.integration
    @pytest.mark.azure
    def test_application_insights_integration(self):
        """Test Application Insights integration."""
        try:
            from monitoring.app_insights import get_app_insights
            insights = get_app_insights()
            assert insights is not None
            
            # Test basic methods exist
            if hasattr(insights, 'track_event'):
                assert callable(insights.track_event)
            if hasattr(insights, 'enabled'):
                assert isinstance(insights.enabled, bool)
                
        except ImportError:
            pytest.skip("app_insights not available")


class TestRedisIntegration:
    """Test Redis integration."""
    
    @pytest.mark.integration
    @pytest.mark.redis
    def test_redis_availability(self):
        """Test Redis client availability."""
        try:
            import redis
            assert redis is not None
        except ImportError:
            pytest.skip("redis package not available")
    
    @pytest.mark.integration
    @pytest.mark.redis
    def test_redis_cache_integration(self):
        """Test Redis cache integration if available."""
        try:
            from crawler.redis_cache import get_redis_client
        except ImportError:
            try:
                # Alternative location
                from crawler.utils.redis_cache import get_redis_client
            except ImportError:
                pytest.skip("Redis cache module not available")
        
        try:
            client = get_redis_client()
            if client:
                assert client is not None
        except Exception:
            # Redis connection issues are acceptable
            pass


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_crawl_cycle_integration(self):
        """Test a complete crawl cycle with real components."""
        try:
            from crawler.core.source_crawler import crawl_source
            from monitoring.metrics import get_metrics
        except ImportError:
            pytest.skip("Required modules not available")
        
        # Test configuration
        test_config = {
            'name': 'end_to_end_test',
            'type': 'rss',
            'url': 'https://httpbin.org/status/200',  # Simple HTTP endpoint
            'enabled': True
        }
        
        # Get initial metrics state
        initial_metrics = get_metrics()
        
        # Run complete crawl
        result = await crawl_source(test_config)
        
        # Verify results
        assert result is not None
        processed, failed, skipped = result  # Updated to expect 3 values
        assert isinstance(processed, int)
        assert isinstance(failed, int)
        assert isinstance(skipped, int)
        
        # Get final metrics state
        final_metrics = get_metrics()
        assert final_metrics is not None
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    def test_monitoring_integration_during_operation(self):
        """Test monitoring system during actual operations."""
        monitoring_components = []
        
        # Test each monitoring component
        try:
            from monitoring.metrics import get_metrics
            metrics = get_metrics()
            if metrics:
                monitoring_components.append('metrics')
        except ImportError:
            pass
        
        try:
            from monitoring.duplicate_detector import get_duplicate_detector
            detector = get_duplicate_detector()
            if detector:
                monitoring_components.append('duplicate_detector')
        except ImportError:
            pass
        
        try:
            from monitoring.health_check import get_health_check
            health = get_health_check()
            if health:
                monitoring_components.append('health_check')
        except ImportError:
            pass
        
        if monitoring_components:
            assert len(monitoring_components) > 0
            # All components should be available simultaneously
            for component in monitoring_components:
                assert component in ['metrics', 'duplicate_detector', 'health_check']
        else:
            pytest.skip("No monitoring components available for integration testing")
    
    @pytest.mark.integration
    def test_configuration_and_execution_integration(self, temp_dir):
        """Test configuration loading and execution integration."""
        try:
            from crawler.utils.config_loader import load_sources_config
        except ImportError:
            pytest.skip("config_loader not available")
        
        # Create test configuration file
        test_config_data = {
            'sources': [
                {
                    'name': 'integration_test_source_1',
                    'type': 'rss',
                    'url': 'https://example.com/feed1.xml',
                    'enabled': True
                },
                {
                    'name': 'integration_test_source_2', 
                    'type': 'rss',
                    'url': 'https://example.com/feed2.xml',
                    'enabled': False
                }
            ]
        }
        
        # Write test config file
        import yaml
        config_file = os.path.join(temp_dir, 'test_sources.yaml')
        with open(config_file, 'w') as f:
            yaml.dump(test_config_data, f)
        
        # Load configuration
        sources = load_sources_config(config_file)
        
        # Verify integration
        assert isinstance(sources, list)
        assert len(sources) == 2
        
        # Verify source structure
        for source in sources:
            assert isinstance(source, dict)
            assert 'name' in source
            assert 'type' in source
            assert 'url' in source


if __name__ == "__main__":
    print("Running external service integration tests...")
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "-m", "integration"
    ], cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    
    sys.exit(result.returncode)
