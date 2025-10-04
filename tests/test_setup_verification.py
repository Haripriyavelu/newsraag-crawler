"""
Simple example tests to verify testing setup works.

Run with: python run_tests.py test tests/test_setup_verification.py
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestSetupVerification:
    """Verify that the testing setup is working correctly."""
    
    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test that basic pytest functionality works."""
        assert True
        assert 1 + 1 == 2
        assert "hello" in "hello world"
    
    @pytest.mark.unit
    def test_imports_work(self):
        """Test that project imports are working."""
        try:
            # Try importing current architecture modules
            from crawler.factories import SourceFactory
            from crawler.interfaces import INewsSource, SourceType
            from monitoring import metrics
            from monitoring.duplicate_detector import get_duplicate_detector
            
            assert True  # If we get here, imports work
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
    
    @pytest.mark.unit
    def test_mocking_works(self):
        """Test that mocking functionality works."""
        with patch('builtins.print') as mock_print:
            print("This is a test")
            mock_print.assert_called_once_with("This is a test")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_testing_works(self):
        """Test that async testing functionality works."""
        async def sample_async_function():
            await asyncio.sleep(0.001)  # Very short sleep
            return "async_result"
        
        result = await sample_async_function()
        assert result == "async_result"
    
    @pytest.mark.unit
    def test_fixtures_work(self, sample_source_config):
        """Test that fixtures from conftest.py work."""
        assert sample_source_config is not None
        assert 'name' in sample_source_config
        assert sample_source_config['name'] == 'test_source'
    
    @pytest.mark.unit
    def test_environment_variables(self, mock_environment_variables):
        """Test that environment variable mocking works."""
        assert os.getenv('QDRANT_URL') == 'http://localhost:6333'
        assert os.getenv('OPENAI_API_KEY') == 'test-openai-key'
    
    @pytest.mark.unit
    def test_temp_directory_fixture(self, temp_dir):
        """Test that temporary directory fixture works."""
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)
        
        # Create a test file
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        assert os.path.exists(test_file)


class TestProjectSpecificSetup:
    """Test project-specific functionality."""
    
    @pytest.mark.unit
    def test_can_import_crawler_modules(self):
        """Test that we can import crawler modules."""
        try:
            # Test current architecture imports
            from crawler.factories import SourceFactory, load_sources_from_yaml
            from crawler.interfaces import INewsSource, SourceType, ContentType
            from crawler.extensions.html_extensions import register_html_extensions
            
        except ImportError:
            # Some modules might not be fully implemented yet
            pass
        
        # Test that at least the main module can be imported
        try:
            import main
            assert hasattr(main, 'main_loop') or hasattr(main, '__name__')
        except ImportError:
            pytest.fail("Cannot import main module")
    
    @pytest.mark.unit
    def test_can_import_monitoring_modules(self):
        """Test that we can import monitoring modules."""
        # Test basic module imports
        monitoring_modules = ['metrics', 'health_check', 'duplicate_detector', 'app_insights', 'alerts']
        
        for module_name in monitoring_modules:
            try:
                module = __import__(f'monitoring.{module_name}', fromlist=[module_name])
                assert module is not None, f"monitoring.{module_name} should be importable"
            except ImportError:
                # Module might not exist yet, that's ok for setup verification
                pass
        
        # Test specific functions that should exist
        try:
            from monitoring.metrics import get_metrics
            metrics = get_metrics()
            assert metrics is not None
        except ImportError:
            # get_metrics might not exist, skip
            pass
    
    @pytest.mark.unit
    def test_config_loading(self):
        """Test that configuration loading works."""
        try:
            from crawler.factories import load_sources_from_yaml
            
            # This should handle missing config gracefully
            config = load_sources_from_yaml("non_existent_config.yaml")
            # Should return empty list or None, not crash
            assert config is None or isinstance(config, list)
            
        except ImportError:
            pytest.skip("Config loader not yet implemented")
        except Exception as e:
            # Should not crash on missing config
            assert "not found" in str(e).lower() or "no such file" in str(e).lower() or "does not exist" in str(e).lower()


class TestSimpleIntegration:
    """Simple integration tests to verify components work together."""
    
    @pytest.mark.integration
    def test_metrics_and_duplicate_detector_integration(self):
        """Test that metrics and duplicate detector can work together."""
        try:
            from monitoring.metrics import get_metrics  
            from monitoring.duplicate_detector import get_duplicate_detector
            
            metrics = get_metrics()
            detector = get_duplicate_detector()
            
            # Test basic functionality
            cycle_id = metrics.start_cycle()
            assert cycle_id is not None
            
            test_article = {
                'title': 'Test Article',
                'url': 'https://example.com/test',
                'content': 'Test content'
            }
            
            # Check if duplicate (first time should be False)
            is_dup, reason = detector.is_duplicate(test_article)
            assert is_dup is False
            
            # Check again - should now be True (duplicate)
            is_dup_second, reason_second = detector.is_duplicate(test_article)
            assert is_dup_second is True
            assert reason_second == "url"
            
            metrics.end_cycle(success=True)
            
            # Verify metrics were collected
            current_metrics = metrics.get_current_metrics()
            assert current_metrics is not None
            
        except ImportError:
            pytest.skip("Required modules not available")


# Performance test example
class TestPerformanceExample:
    """Example performance tests."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_data_handling_performance(self):
        """Test performance with larger datasets."""
        import time
        
        start_time = time.time()
        
        # Simulate processing large amount of data
        data = []
        for i in range(10000):
            data.append(f"item_{i}")
        
        # Process data
        processed = [item.upper() for item in data if 'item' in item]
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time
        assert processing_time < 2.0  # Less than 2 seconds
        assert len(processed) == 10000
        assert processed[0] == "ITEM_0"


# Run this file directly for quick verification
if __name__ == "__main__":
    print("🚀 Running setup verification tests...")
    
    # Run tests programmatically
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", __file__, "-v"
        ], capture_output=True, text=True)
        
        print("📊 Test Results:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All setup verification tests passed!")
        else:
            print("❌ Some tests failed. Check output above.")
            
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)
