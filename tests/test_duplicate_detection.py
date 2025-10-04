#!/usr/bin/env python3
"""
Test script to check duplicate detection functionality.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
import time

def test_duplicate_detection():
    """Test the duplicate detection system."""
    logger.info("🧪 Testing duplicate detection system...")
    
    try:
        # Import duplicate detector
        from monitoring.duplicate_detector import get_duplicate_detector
        
        # Get detector instance
        detector = get_duplicate_detector()
        logger.info(f"✅ Successfully imported duplicate detector: {type(detector).__name__}")
        
        # Test article 1
        test_article_1 = {
            'url': 'https://example.com/test-article-1',
            'title': 'Test Article: Market Analysis',
            'content': 'This is test content for market analysis.'
        }
        
        # Test article 2 (same URL - should be duplicate)
        test_article_2 = {
            'url': 'https://example.com/test-article-1',  # Same URL
            'title': 'Test Article: Updated Market Analysis', 
            'content': 'Updated content for market analysis.'
        }
        
        # Test article 3 (same title - should be duplicate)
        test_article_3 = {
            'url': 'https://example.com/test-article-3',  # Different URL
            'title': 'Test Article: Market Analysis',      # Same title
            'content': 'Different content but same title.'
        }
        
        # Test article 4 (completely different - should not be duplicate)
        test_article_4 = {
            'url': 'https://example.com/test-article-4',
            'title': 'Different Article: Forex Update',
            'content': 'Completely different content about forex.'
        }
        
        # Test 1: First article should not be duplicate
        logger.info("🔍 Test 1: First article (should not be duplicate)")
        is_dup_1, dup_type_1 = detector.is_duplicate(test_article_1)
        logger.info(f"   Result: is_duplicate={is_dup_1}, type={dup_type_1}")
        
        if is_dup_1:
            logger.error("❌ Test 1 FAILED: First article should not be duplicate")
            return False
        else:
            logger.info("✅ Test 1 PASSED: First article correctly identified as unique")
        
        time.sleep(1)  # Small delay
        
        # Test 2: Same URL should be duplicate
        logger.info("🔍 Test 2: Same URL (should be duplicate)")
        is_dup_2, dup_type_2 = detector.is_duplicate(test_article_2)
        logger.info(f"   Result: is_duplicate={is_dup_2}, type={dup_type_2}")
        
        if not is_dup_2 or dup_type_2 != 'url':
            logger.error("❌ Test 2 FAILED: Same URL should be detected as duplicate")
            return False
        else:
            logger.info("✅ Test 2 PASSED: Same URL correctly identified as duplicate")
        
        time.sleep(1)  # Small delay
        
        # Test 3: Same title should be duplicate
        logger.info("🔍 Test 3: Same title (should be duplicate)")
        is_dup_3, dup_type_3 = detector.is_duplicate(test_article_3)
        logger.info(f"   Result: is_duplicate={is_dup_3}, type={dup_type_3}")
        
        if not is_dup_3 or dup_type_3 != 'title':
            logger.error("❌ Test 3 FAILED: Same title should be detected as duplicate")
            return False
        else:
            logger.info("✅ Test 3 PASSED: Same title correctly identified as duplicate")
        
        time.sleep(1)  # Small delay
        
        # Test 4: Different article should not be duplicate
        logger.info("🔍 Test 4: Different article (should not be duplicate)")
        is_dup_4, dup_type_4 = detector.is_duplicate(test_article_4)
        logger.info(f"   Result: is_duplicate={is_dup_4}, type={dup_type_4}")
        
        if is_dup_4:
            logger.error("❌ Test 4 FAILED: Different article should not be duplicate")
            return False
        else:
            logger.info("✅ Test 4 PASSED: Different article correctly identified as unique")
        
        # Test cache info
        logger.info("🔍 Cache information:")
        cache_type = "Redis" if detector.use_redis else "In-memory"
        logger.info(f"   Cache type: {cache_type}")
        logger.info(f"   Cache expiry: {detector.cache_expiry_seconds} seconds ({detector.cache_expiry_seconds/3600} hours)")
        
        if not detector.use_redis:
            logger.info(f"   URLs in cache: {len(detector.url_cache)}")
            logger.info(f"   Titles in cache: {len(detector.title_cache)}")
            for url, expiry in detector.url_cache.items():
                logger.info(f"     URL: {url[:60]}... (expires: {expiry})")
            for title, expiry in detector.title_cache.items():
                logger.info(f"     Title: {title[:60]}... (expires: {expiry})")
        
        logger.info("🎉 All duplicate detection tests PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Duplicate detection test FAILED: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

def test_title_normalization():
    """Test title normalization functionality."""
    logger.info("🧪 Testing title normalization...")
    
    try:
        from monitoring.duplicate_detector import DuplicateDetector
        detector = DuplicateDetector()
        
        # Test different variations of the same title
        titles = [
            "Market Analysis: Forex Update",
            "market analysis: forex update",
            "Market Analysis:  Forex   Update",  # Extra spaces
            "Market Analysis! Forex Update?",    # Punctuation
            "MARKET ANALYSIS: FOREX UPDATE",     # All caps
        ]
        
        normalized_titles = [detector._normalize_title(title) for title in titles]
        
        logger.info("📋 Title normalization results:")
        for i, (original, normalized) in enumerate(zip(titles, normalized_titles)):
            logger.info(f"   {i+1}. '{original}' → '{normalized}'")
        
        # All normalized titles should be the same
        unique_normalized = set(normalized_titles)
        if len(unique_normalized) == 1:
            logger.info("✅ Title normalization PASSED: All variations normalized to same result")
            return True
        else:
            logger.error(f"❌ Title normalization FAILED: Got {len(unique_normalized)} different results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Title normalization test FAILED: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting duplicate detection tests...")
    
    # Test duplicate detection
    duplicate_test_passed = test_duplicate_detection()
    
    # Test title normalization
    normalization_test_passed = test_title_normalization()
    
    # Summary
    logger.info("="*60)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Duplicate Detection Test: {'✅ PASSED' if duplicate_test_passed else '❌ FAILED'}")
    logger.info(f"Title Normalization Test: {'✅ PASSED' if normalization_test_passed else '❌ FAILED'}")
    
    if duplicate_test_passed and normalization_test_passed:
        logger.info("🎉 ALL TESTS PASSED! Duplicate detection is working correctly.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests FAILED. Please check the implementation.")
        sys.exit(1)
