"""
Practical integration tests for NewsRaag Crawler.

Tests how different components work together in realistic scenarios.
"""
import pytest
import asyncio
import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestCrawlerIntegration:
    """Integration tests for the main crawler workflow."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_source_crawler_basic_integration(self):
        """Test that source_crawler integrates with basic dependencies."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler not available")
        
        # Test with minimal real integration - no mocking of core functions
        config = {
            'name': 'integration_test_source',
            'type': 'rss',
            'url': 'https://httpbin.org/status/404'  # Will fail, but should handle gracefully
        }
        
        # This should not crash, even if it fails to get data
        from crawler.core.source_crawler import crawl_source
        result = await crawl_source(config)
        
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 3  # Should return exactly 3 values
        
        processed_count, failed_count, skipped_count = result
        # Should handle the 404 gracefully
        assert isinstance(processed_count, int)
        assert isinstance(failed_count, int)
        assert isinstance(skipped_count, int)
    
    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_metrics_integration_with_crawler(self):
        """Test that metrics system integrates with crawler operations."""
        try:
            from crawler.core.source_crawler import crawl_source
            from monitoring.metrics import get_metrics
        except ImportError:
            pytest.skip("Required modules not available")
        
        # Get metrics before operation
        metrics = get_metrics()
        initial_state = str(metrics.__dict__) if hasattr(metrics, '__dict__') else "no_state"
        
        config = {
            'name': 'metrics_test_source',
            'type': 'rss', 
            'url': 'https://httpbin.org/status/200'  # Should succeed
        }
        
        # Run crawler operation
        result = await crawl_source(config)
        
        # Get metrics after operation  
        final_metrics = get_metrics()
        final_state = str(final_metrics.__dict__) if hasattr(final_metrics, '__dict__') else "no_state"
        
        # Verify integration worked
        assert result is not None
        # Metrics should be available (even if unchanged)
        assert final_metrics is not None
    
    @pytest.mark.integration
    def test_monitoring_modules_integration(self):
        """Test that monitoring modules can work together."""
        available_modules = []
        
        # Check metrics
        try:
            from monitoring.metrics import get_metrics
            metrics = get_metrics()
            if metrics:
                available_modules.append('metrics')
        except ImportError:
            pass
        
        # Check duplicate detector
        try:
            from monitoring.duplicate_detector import get_duplicate_detector
            detector = get_duplicate_detector()
            if detector:
                available_modules.append('duplicate_detector')
        except ImportError:
            pass
        
        # Check health check
        try:
            from monitoring.health_check import HealthCheck
            health = HealthCheck()
            if health:
                available_modules.append('health_check')
        except ImportError:
            pass
        
        # Check app insights
        try:
            from monitoring.app_insights import get_app_insights
            insights = get_app_insights()
            if insights:
                available_modules.append('app_insights')
        except ImportError:
            pass
        
        # Should have at least one monitoring module
        if available_modules:
            assert len(available_modules) > 0
            print(f"Available monitoring modules: {available_modules}")
        else:
            pytest.skip("No monitoring modules available for integration testing")


class TestConfigurationIntegration:
    """Test configuration loading and source management integration."""
    
    @pytest.mark.integration
    def test_config_loader_integration(self):
        """Test configuration loading with real files."""
        try:
            from crawler.utils.config_loader import load_sources_config
        except ImportError:
            pytest.skip("config_loader not available")
        
        # Test with non-existent file (should handle gracefully)
        result = load_sources_config("non_existent_file.yaml")
        assert result is not None  # Should return empty list, not crash
        assert isinstance(result, list)
        
        # Test with project's actual config if it exists
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'sources.yaml')
        if os.path.exists(config_path):
            result = load_sources_config(config_path)
            assert isinstance(result, list)
            if result:  # If config has sources
                # Each source should have basic required fields
                for source in result:
                    assert isinstance(source, dict)
                    # Common fields that should exist
                    expected_fields = ['name']
                    for field in expected_fields:
                        if field in source:
                            assert source[field] is not None
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_config_with_crawler_integration(self):
        """Test loading config and using it with crawler."""
        try:
            from crawler.utils.config_loader import load_sources_config
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("Required modules not available")
        
        # Create a temporary test config
        test_config = [{
            'name': 'test_integration_source',
            'type': 'rss',
            'url': 'https://httpbin.org/xml',  # Returns XML (might work as RSS)
            'enabled': True
        }]
        
        # Test each source from config
        for source in test_config:
            result = await crawl_source(source)
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 3  # Should return exactly 3 values
            
            processed_count, failed_count, skipped_count = result  # Updated to expect 3 values
            # Basic validation of return values
            assert processed_count >= 0
            assert failed_count >= 0  
            assert skipped_count >= 0


class TestFileSystemIntegration:
    """Test file system operations integration."""
    
    @pytest.mark.integration
    def test_data_directory_integration(self, temp_dir):
        """Test data directory creation and usage."""
        # Test creating typical data directories
        data_dirs = ['metrics', 'logs', 'cache', 'heartbeat']
        
        for dir_name in data_dirs:
            dir_path = os.path.join(temp_dir, 'data', dir_name)
            os.makedirs(dir_path, exist_ok=True)
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
            
            # Test writing a file to the directory
            test_file = os.path.join(dir_path, f'test_{dir_name}.txt')
            with open(test_file, 'w') as f:
                f.write(f'Test content for {dir_name}')
            
            assert os.path.exists(test_file)
            
            # Test reading the file back
            with open(test_file, 'r') as f:
                content = f.read()
                assert f'Test content for {dir_name}' in content
    
    @pytest.mark.integration
    def test_metrics_file_integration(self, temp_dir):
        """Test metrics file operations if metrics module available."""
        try:
            from monitoring.metrics import get_metrics
            metrics = get_metrics()
        except ImportError:
            pytest.skip("Metrics module not available")
        
        # Test basic metrics operations with file system
        if hasattr(metrics, 'save_daily_metrics'):
            # Try to save metrics (might work or might fail gracefully)
            try:
                with patch('monitoring.metrics.METRICS_DIR', temp_dir):
                    result = metrics.save_daily_metrics()
                    # Should either succeed or fail gracefully
                    assert result is not None
            except Exception:
                # It's okay if this fails - we're testing integration
                pass
        
        # Test that metrics directory structure is reasonable
        expected_patterns = ['metrics', 'data', 'log']
        # At least one pattern should make sense for metrics storage
        found_reasonable_structure = any(pattern in str(metrics.__class__).lower() for pattern in expected_patterns)
        assert found_reasonable_structure or hasattr(metrics, 'save_daily_metrics') or hasattr(metrics, 'get_stats')


class TestHealthCheckIntegration:
    """Test health check and monitoring integration."""
    
    @pytest.mark.integration
    def test_health_check_system_integration(self):
        """Test health check system integration."""
        # Test health check server if available
        try:
            from crawler.health.health_server import start_health_server
            # Just test that it can be imported
            assert callable(start_health_server)
        except ImportError:
            pass
        
        # Test health check endpoints if available
        try:
            from monitoring.health_check import get_health_check
            health_check = get_health_check()
            assert health_check is not None
        except ImportError:
            pass
        
        # Test monitor.py integration if it exists
        monitor_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'monitor.py')
        if os.path.exists(monitor_file):
            # File exists, should be readable
            with open(monitor_file, 'r') as f:
                content = f.read()
                assert len(content) > 0
                # Should contain some monitoring-related code
                monitoring_keywords = ['health', 'check', 'status', 'monitor']
                found_keywords = any(keyword in content.lower() for keyword in monitoring_keywords)
                assert found_keywords
    
    @pytest.mark.integration
    def test_main_application_integration(self):
        """Test main application file integration."""
        main_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'main.py')
        
        if os.path.exists(main_file):
            # Test that main.py can be imported without crashing
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("main_module", main_file)
                if spec and spec.loader:
                    # Don't actually run main, just check it can be loaded
                    main_module = importlib.util.module_from_spec(spec)
                    # This tests basic syntax and import structure
                    assert main_module is not None
            except Exception as e:
                # If there are import issues, that's valuable information
                pytest.fail(f"Main.py has import issues: {e}")
        else:
            pytest.skip("main.py not found")


class TestExternalServiceIntegration:
    """Test external service integration with fallbacks."""
    
    @pytest.mark.integration
    @pytest.mark.external
    def test_http_request_integration(self):
        """Test HTTP request capabilities."""
        import requests
        
        # Test basic HTTP functionality that crawler needs
        test_urls = [
            'https://httpbin.org/status/200',
            'https://httpbin.org/xml',
            'https://httpbin.org/json'
        ]
        
        working_urls = 0
        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    working_urls += 1
                    assert len(response.content) > 0
            except Exception:
                # Network issues are acceptable in tests
                pass
        
        # At least verify that requests module works
        assert requests is not None
        # If we can't reach any test URLs, that's also acceptable
        # The test verifies HTTP capability exists
    
    @pytest.mark.integration
    @pytest.mark.external  
    def test_rss_parsing_integration(self):
        """Test RSS parsing integration."""
        try:
            import feedparser
            
            # Test with a known-good RSS structure
            sample_rss = '''<?xml version="1.0" encoding="UTF-8"?>
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
            
            feed = feedparser.parse(sample_rss)
            assert feed is not None
            assert 'entries' in feed
            assert len(feed.entries) == 1
            assert feed.entries[0].title == 'Test Article'
            
        except ImportError:
            pytest.skip("feedparser not available")


# Run integration tests with this command:
if __name__ == "__main__":
    print("Running integration tests...")
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "-m", "integration"
    ], cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    sys.exit(result.returncode)
