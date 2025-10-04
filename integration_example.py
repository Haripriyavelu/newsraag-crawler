# integration_example.py
"""
Example of how to integrate the new Phase 1 system with existing main.py.
This shows how to replace the current source management with the new unified system.
"""
import asyncio
from typing import Dict, Any

# New system imports
from crawler.factories import SourceFactory, load_sources_from_yaml
from crawler.interfaces import INewsSource


async def new_main_loop():
    """
    Enhanced main loop using the new unified source system.
    This can replace the existing main loop in main.py.
    """
    print("🚀 Starting NewsRagnarok with unified source system...")
    
    # Option 1: Load sources from YAML configuration
    try:
        configs = load_sources_from_yaml("config/sources.yaml")
        if configs:
            sources = SourceFactory.create_sources_from_config_list(configs)
            print(f"✅ Loaded {len(sources)} sources from configuration")
        else:
            # Fallback to creating all existing sources
            sources = create_all_sources_fallback()
    except Exception as e:
        print(f"⚠️ Config loading failed: {e}")
        # Fallback to creating all existing sources
        sources = create_all_sources_fallback()
    
    if not sources:
        print("❌ No sources available. Exiting.")
        return
    
    print(f"🎯 Active sources: {list(sources.keys())}")
    
    # Main processing loop
    while True:
        print("\n" + "="*60)
        print("🔄 Starting new crawl cycle...")
        
        cycle_stats = {
            'total_articles_discovered': 0,
            'total_articles_processed': 0, 
            'total_articles_failed': 0,
            'source_results': {}
        }
        
        # Process each source using unified interface
        for source_name, source in sources.items():
            try:
                print(f"\n📡 Processing source: {source_name}")
                
                # Health check
                if not await source.health_check():
                    print(f"⚠️ Source {source_name} failed health check, skipping...")
                    continue
                
                # Process articles using template method
                result = await source.process_articles()
                
                # Aggregate statistics
                cycle_stats['total_articles_discovered'] += result['articles_discovered']
                cycle_stats['total_articles_processed'] += result['articles_processed']
                cycle_stats['total_articles_failed'] += result['articles_failed']
                cycle_stats['source_results'][source_name] = result
                
                print(f"✅ {source_name}: {result['articles_processed']}/{result['articles_discovered']} processed")
                
            except Exception as e:
                print(f"❌ Error processing {source_name}: {e}")
                cycle_stats['source_results'][source_name] = {
                    'error': str(e),
                    'articles_processed': 0,
                    'articles_discovered': 0,
                    'articles_failed': 1
                }
        
        # Cycle summary
        print(f"\n📊 Cycle Summary:")
        print(f"   Articles discovered: {cycle_stats['total_articles_discovered']}")
        print(f"   Articles processed: {cycle_stats['total_articles_processed']}")
        print(f"   Articles failed: {cycle_stats['total_articles_failed']}")
        
        success_rate = (cycle_stats['total_articles_processed'] / 
                       max(1, cycle_stats['total_articles_discovered'])) * 100
        print(f"   Success rate: {success_rate:.1f}%")
        
        # Sleep until next cycle (maintaining existing 1-hour interval)
        print(f"\n💤 Sleeping for 3600 seconds until next cycle...")
        await asyncio.sleep(3600)


def create_all_sources_fallback() -> Dict[str, INewsSource]:
    """
    Fallback method to create all sources programmatically.
    Use this if YAML config loading fails.
    """
    from crawler.interfaces import SourceType, ContentType, SourceConfig
    
    try:
        print("📋 Creating sources programmatically...")
        
        # Define all 5 existing sources
        source_configs = [
            SourceConfig(
                name="babypips",
                source_type=SourceType.RSS,
                content_type=ContentType.FOREX,
                base_url="https://www.babypips.com",
                rss_url="https://www.babypips.com/feed.rss",
                rate_limit_seconds=2,
                max_articles_per_run=50,
                custom_processing=True
            ),
            SourceConfig(
                name="fxstreet", 
                source_type=SourceType.RSS,
                content_type=ContentType.FOREX,
                base_url="https://www.fxstreet.com",
                rss_url="https://www.fxstreet.com/rss/news",
                rate_limit_seconds=1,
                max_articles_per_run=50,
                custom_processing=True
            ),
            SourceConfig(
                name="forexlive",
                source_type=SourceType.RSS,
                content_type=ContentType.FOREX,
                base_url="https://www.forexlive.com", 
                rss_url="https://www.forexlive.com/feed/",
                rate_limit_seconds=1,
                max_articles_per_run=50,
                custom_processing=True
            ),
            SourceConfig(
                name="kabutan",
                source_type=SourceType.HTML_SCRAPING,
                content_type=ContentType.STOCKS,
                base_url="https://kabutan.jp/news/marketnews/",
                rate_limit_seconds=2,
                max_articles_per_run=30,
                requires_translation=True,
                custom_processing=True
            ),
            SourceConfig(
                name="poundsterlinglive",
                source_type=SourceType.HTML_SCRAPING,
                content_type=ContentType.FOREX,
                base_url="https://www.poundsterlinglive.com/markets",
                rate_limit_seconds=2,
                max_articles_per_run=40,
                custom_processing=True
            )
        ]
        
        # Create sources using factory
        sources = SourceFactory.create_sources_from_config_list(source_configs)
        return sources
        
    except Exception as e:
        print(f"❌ Failed to create sources: {e}")
        return {}


def show_source_info():
    """Display information about available sources and factory capabilities."""
    print("🔍 NewsRagnarok Source System Information")
    print("="*50)
    
    # Show factory capabilities
    print("\n📚 Available Templates:")
    for source_type in SourceFactory.get_supported_source_types():
        print(f"   - {source_type.value}")
    
    print("\n🔧 Custom Adapters:")
    for source_name in SourceFactory.get_custom_sources():
        info = SourceFactory.get_creation_info(source_name)
        print(f"   - {source_name}: {info['creation_strategy']} ({info['adapter_class']})")
    
    print("\n💡 Usage Examples:")
    print("   1. Load from YAML: load_sources_from_yaml('config/sources.yaml')")
    print("   2. Create programmatically: SourceFactory.create_source(config)")
    print("   3. Create all existing: create_all_sources_fallback()")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        show_source_info()
    else:
        print("🌟 NewsRagnarok Unified Source System Integration Example")
        print("Run 'python integration_example.py info' to see system information")
        print("Run 'python integration_example.py' to start the enhanced main loop")
        
        # For demo, just show info
        show_source_info()
        
        print("\n🚀 To integrate with main.py:")
        print("   1. Replace existing source imports with: from crawler.factories import SourceFactory")
        print("   2. Replace source creation with: sources = SourceFactory.create_sources_from_config_list(configs)")
        print("   3. Replace individual source processing with: await source.process_articles()")
        print("   4. All existing monitoring and storage will work unchanged!")
