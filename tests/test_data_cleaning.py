#!/usr/bin/env python3
"""
Quick test for data cleaning setup.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

def test_data_cleaning():
    """Test data cleaning setup quickly."""
    logger.info("🧪 Testing data cleaning setup...")
    
    try:
        # Test environment variables
        env_vars = {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'AZURE_OPENAI_DEPLOYMENT': os.environ.get('AZURE_OPENAI_DEPLOYMENT'), 
            'OPENAI_BASE_URL': os.environ.get('OPENAI_BASE_URL'),
            'LLM_CLEANING_ENABLED': os.environ.get('LLM_CLEANING_ENABLED')
        }
        
        logger.info("📋 Environment variables:")
        for key, value in env_vars.items():
            status = "✅ SET" if value else "❌ MISSING"
            masked_value = f"{value[:10]}..." if value and len(value) > 10 else value
            logger.info(f"   {key}: {status} ({masked_value})")
        
        # Test LLM cleaner import
        try:
            from utils.llm.cleaner import LLMContentCleaner
            logger.info("✅ LLM cleaner module imported successfully")
            
            # Initialize cleaner
            cleaner = LLMContentCleaner()
            logger.info(f"✅ LLM cleaner initialized with model: {cleaner.model}")
            logger.info(f"📊 Token limit per request: {cleaner.token_limit}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ LLM cleaner error: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_data_cleaning()
    if success:
        logger.info("🎉 Data cleaning is properly configured!")
    else:
        logger.error("❌ Data cleaning has issues")
    sys.exit(0 if success else 1)
