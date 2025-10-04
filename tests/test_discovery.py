#!/usr/bin/env python3
"""
Test the hierarchical discovery service fix
"""
import asyncio
from crawler.factories.config_loader import load_sources_from_yaml
from crawler.factories.source_factory import SourceFactory

async def test_discovery():
    print("Testing hierarchical discovery service...")
    
    # Load one source config for testing
    configs = load_sources_from_yaml("config/sources.yaml")
    if not configs:
        print("❌ No configs loaded")
        return
    
    # Test babypips first
    for config in configs:
        if config.name == "babypips":
            print(f"\nTesting {config.name}...")
            
            # Create source
            source = SourceFactory.create_source(config)
            if not source:
                print(f"❌ Failed to create source for {config.name}")
                continue
            
            print(f"Source created: {config.name}")
            
            # Test discovery service directly
            discovery_service = source.get_discovery_service()
            print(f"Discovery service created: {type(discovery_service).__name__}")
            
            # Test article discovery
            articles = []
            async for article in discovery_service.discover_articles():
                articles.append(article)
                print(f"Found article: {article.title[:80]}...")
                if len(articles) >= 3:  # Limit for testing
                    break
            
            print(f"{config.name}: Found {len(articles)} articles via discovery service")
            
            # Test process_articles
            print(f"\nTesting process_articles for {config.name}...")
            result = await source.process_articles()
            print(f"📊 Process result: {result}")
            
            break

if __name__ == "__main__":
    asyncio.run(test_discovery())
