#!/usr/bin/env python3
"""
Test health check fix.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.factories import load_sources_from_yaml, SourceFactory

async def test_health_check():
    """Test if health check works now."""
    try:
        print("Loading sources...")
        sources_config = load_sources_from_yaml('config/sources.yaml')
        
        print(f"Testing health check for {sources_config[0].name}...")
        source = SourceFactory.create_source(sources_config[0])  # babypips
        
        print("Running health check...")
        is_healthy = await source.health_check()
        
        print(f"Health check result: {'PASS' if is_healthy else 'FAIL'}")
        return is_healthy
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_health_check())
    print(f"\nHealth check test: {'SUCCESS' if result else 'FAILED'}")
