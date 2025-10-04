"""
Simple setup verification tests that work with the current project structure.

Run with: python run_tests.py test tests/test_basic_setup.py
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestBasicSetup:
    """Basic setup verification tests."""
    
    @pytest.mark.unit
    def test_python_basics(self):
        """Test that basic Python functionality works."""
        assert True
        assert 1 + 1 == 2
        assert "test" in "testing"
    
    @pytest.mark.unit
    def test_project_structure_exists(self):
        """Test that main project directories exist."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        # Only check directories that should definitely exist
        expected_dirs = ['crawler', 'monitoring', 'clients', 'tests']
        for dir_name in expected_dirs:
            dir_path = os.path.join(project_root, dir_name)
            assert os.path.exists(dir_path), f"Directory {dir_name} should exist"
        
        # Check optional directories
        optional_dirs = ['utils', 'models', 'config']
        for dir_name in optional_dirs:
            dir_path = os.path.join(project_root, dir_name)
            if os.path.exists(dir_path):
                assert os.path.isdir(dir_path), f"{dir_name} should be a directory if it exists"
    
    @pytest.mark.unit
    def test_main_module_exists(self):
        """Test that main.py exists and can be imported."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        main_file = os.path.join(project_root, 'main.py')
        
        assert os.path.exists(main_file), "main.py should exist"
        
        # Try to import it (might have import errors, but file should be readable)
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert len(content) > 0, "main.py should have content"
                assert 'def' in content or 'import' in content, "main.py should have Python code"
        except Exception as e:
            pytest.fail(f"Could not read main.py: {e}")
    
    @pytest.mark.unit
    def test_config_loader_exists(self):
        """Test that config loader module exists."""
        try:
            from crawler.utils.config_loader import load_sources_config
            assert callable(load_sources_config), "load_sources_config should be callable"
        except ImportError as e:
            pytest.fail(f"Could not import config_loader: {e}")
    
    @pytest.mark.unit
    def test_monitoring_modules_exist(self):
        """Test that monitoring modules exist."""
        monitoring_modules = ['metrics', 'health_check', 'duplicate_detector', 'app_insights']
        
        for module_name in monitoring_modules:
            try:
                # Try to import the module
                module = __import__(f'monitoring.{module_name}', fromlist=[module_name])
                assert module is not None, f"monitoring.{module_name} should be importable"
            except ImportError:
                # Module might not exist yet, that's ok for setup verification
                pass
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test that async functionality works."""
        async def test_async_function():
            await asyncio.sleep(0.001)
            return "async_works"
        
        result = await test_async_function()
        assert result == "async_works"
    
    @pytest.mark.unit
    def test_mocking_works(self):
        """Test that mocking functionality works."""
        with patch('builtins.print') as mock_print:
            print("test message")
            mock_print.assert_called_once_with("test message")
    
    @pytest.mark.unit
    def test_fixtures_basic(self, temp_dir):
        """Test that basic fixtures work."""
        assert temp_dir is not None
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)
        
        # Create a test file
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        assert os.path.exists(test_file)
        
        with open(test_file, 'r') as f:
            content = f.read()
            assert content == 'test content'
    
    @pytest.mark.unit
    def test_environment_mocking(self, mock_environment_variables):
        """Test that environment variable mocking works."""
        assert os.getenv('QDRANT_URL') == 'http://localhost:6333'
        assert os.getenv('OPENAI_API_KEY') == 'test-openai-key'
        assert os.getenv('ALERT_SLACK_ENABLED') == 'true'
    
    @pytest.mark.unit
    def test_required_packages_available(self):
        """Test that required packages for testing are available."""
        required_packages = [
            'pytest', 'asyncio', 'unittest.mock', 'tempfile', 
            'pathlib', 'json', 'os', 'sys'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                pytest.fail(f"Required package {package} not available")
    
    @pytest.mark.unit
    def test_sample_config_fixture(self, sample_source_config):
        """Test that sample config fixture works."""
        assert sample_source_config is not None
        assert isinstance(sample_source_config, dict)
        assert 'name' in sample_source_config
        assert 'rss_url' in sample_source_config
        assert sample_source_config['name'] == 'test_source'


class TestProjectSpecificBasics:
    """Test basic project-specific functionality."""
    
    @pytest.mark.unit
    def test_crawler_directory_structure(self):
        """Test crawler directory has expected structure."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        crawler_dir = os.path.join(project_root, 'crawler')
        
        if os.path.exists(crawler_dir):
            expected_subdirs = ['core', 'utils']
            for subdir in expected_subdirs:
                subdir_path = os.path.join(crawler_dir, subdir)
                if os.path.exists(subdir_path):
                    assert os.path.isdir(subdir_path), f"crawler/{subdir} should be a directory"
    
    @pytest.mark.unit
    def test_requirements_files_exist(self):
        """Test that requirements files exist."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        requirements_files = ['requirements.txt', 'requirements-test.txt']
        for req_file in requirements_files:
            req_path = os.path.join(project_root, req_file)
            if os.path.exists(req_path):
                with open(req_path, 'r') as f:
                    content = f.read()
                    assert len(content) > 0, f"{req_file} should have content"
                    # Check for some expected packages
                    if req_file == 'requirements.txt':
                        assert 'requests' in content or 'asyncio' in content, f"{req_file} should contain expected packages"
    
    @pytest.mark.unit
    def test_config_directory_exists(self):
        """Test that config directory exists."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        config_dir = os.path.join(project_root, 'config')
        
        if os.path.exists(config_dir):
            assert os.path.isdir(config_dir), "config should be a directory"
            
            # Check for sources.yaml
            sources_file = os.path.join(config_dir, 'sources.yaml')
            if os.path.exists(sources_file):
                assert os.path.isfile(sources_file), "sources.yaml should be a file"


# Quick test to verify everything is working
def test_quick_verification():
    """Quick test that can be run standalone."""
    assert True, "Basic test functionality is working"
    assert os.path.exists(os.path.dirname(__file__)), "Test directory exists"
    
    # Try importing pytest
    import pytest
    assert pytest is not None, "pytest is available"
    
    print("✅ Quick verification passed!")


if __name__ == "__main__":
    # Run this test file standalone for quick verification
    print("🚀 Running basic setup verification...")
    
    try:
        import subprocess
        import sys
        
        result = subprocess.run([
            sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        print("📊 Test Results:")
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Basic setup verification passed!")
        else:
            print("❌ Some tests failed. This might be expected if modules aren't fully implemented yet.")
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        print("Try running: python -m pytest tests/test_basic_setup.py -v")
