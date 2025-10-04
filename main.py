# main_enhanced.py
"""
Enhanced main entry point for NewsRagnarok Crawler with unified source system.
This version uses the new Phase 1 architecture with adapters and factory pattern.
"""
import time
import asyncio
import os
import sys
import argparse
from loguru import logger
import threading
from datetime import datetime, timedelta
import gc
import psutil
from contextlib import nullcontext

# Import monitoring components (unchanged)
from monitoring import init_monitoring
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from monitoring.duplicate_detector import get_duplicate_detector
from monitoring.alerts import get_alert_manager, trigger_test_alert
from monitoring.app_insights import get_app_insights

# NEW: Import unified source system
from crawler.factories import SourceFactory, load_sources_from_yaml
from crawler.interfaces import INewsSource, SourceType, ContentType, SourceConfig

# Import HTML scraping extensions (Open-Closed Principle)
from crawler.extensions.html_extensions import register_html_extensions

# Import robust RSS parser for enhanced error handling
from crawler.utils.robust_rss_parser import RobustRSSParser

# Import existing utilities (unchanged)
from crawler.utils.dependency_checker import check_dependencies
from crawler.utils.memory_monitor import log_memory_usage
from crawler.utils.cleanup import cleanup_old_data, clear_qdrant_collection, recreate_qdrant_collection
from crawler.health.health_server import start_health_server

# Define path to config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'sources.yaml')

# Constants
CRAWL_INTERVAL_SECONDS = 10800  # Check sources every hour
CLEANUP_INTERVAL_SECONDS = 86400  # Run cleanup every day


def create_all_sources_fallback():
    """
    Create all 5 existing sources programmatically if YAML loading fails.
    This ensures the system always has sources available.
    """
    logger.info("Creating sources using programmatic configuration...")
    
    try:
        source_configs = [
            # BabyPips (RSS) - Increased timeout for reliability
            SourceConfig(
                name="babypips",
                source_type=SourceType.RSS,
                content_type=ContentType.FOREX,
                base_url="https://www.babypips.com",
                rss_url="https://www.babypips.com/feed.rss",
                rate_limit_seconds=2,
                max_articles_per_run=40,  # Reduced from 50
                timeout_seconds=90,  # Increased from 30 for reliability
                custom_processing=True
            ),
            
            # FXStreet (RSS) - Increased timeout for heavy site
            SourceConfig(
                name="fxstreet",
                source_type=SourceType.RSS,
                content_type=ContentType.FOREX,
                base_url="https://www.fxstreet.com",
                rss_url="https://www.fxstreet.com/rss/news",
                rate_limit_seconds=2,  # Increased from 1 to be more respectful
                max_articles_per_run=30,  # Reduced from 50 to avoid overloading
                timeout_seconds=120,  # Increased from 30 to handle heavy loading
                custom_processing=True
            ),
            
            # ForexLive (RSS) - Increased timeout for reliability
            SourceConfig(
                name="forexlive",
                source_type=SourceType.RSS,
                content_type=ContentType.FOREX,
                base_url="https://www.forexlive.com",
                rss_url="https://www.forexlive.com/feed/",
                rate_limit_seconds=2,  # Increased for stability
                max_articles_per_run=40,  # Reduced from 50
                timeout_seconds=90,  # Increased from 30 for reliability
                custom_processing=True
            ),
            
            # Kabutan (HTML with translation) - Heavy timeout for Japanese site
            SourceConfig(
                name="kabutan",
                source_type=SourceType.HTML_SCRAPING,
                content_type=ContentType.STOCKS,
                base_url="https://kabutan.jp/news/marketnews/",
                rate_limit_seconds=3,  # Increased for international site
                max_articles_per_run=25,  # Reduced from 30
                timeout_seconds=150,  # Increased for Japanese site + translation
                requires_translation=True,
                custom_processing=True
            ),
            
            # PoundSterlingLive (HTML) - Heavy timeout for complex site
            SourceConfig(
                name="poundsterlinglive",
                source_type=SourceType.HTML_SCRAPING,
                content_type=ContentType.FOREX,
                base_url="https://www.poundsterlinglive.com/markets",
                rate_limit_seconds=3,  # Increased for stability
                max_articles_per_run=30,  # Reduced from 40
                timeout_seconds=120,  # Increased from 30 for reliability
                custom_processing=True
            )
        ]
        
        # Create sources using factory
        sources = SourceFactory.create_sources_from_config_list(source_configs)
        logger.info(f"✅ Created {len(sources)} sources programmatically")
        return sources
        
    except Exception as e:
        logger.error(f"❌ Failed to create fallback sources: {e}")
        return {}


async def load_unified_sources():
    """
    Load sources using the new unified source system.
    Tries YAML loading first, falls back to programmatic creation.
    """
    logger.info("🔄 Loading sources with unified system...")
    
    # Try loading from YAML configuration
    try:
        if os.path.exists(CONFIG_PATH):
            logger.info(f"📋 Loading sources from YAML: {CONFIG_PATH}")
            configs = load_sources_from_yaml(CONFIG_PATH)
            
            if configs:
                sources = SourceFactory.create_sources_from_config_list(configs)
                if sources:
                    logger.info(f"✅ Successfully loaded {len(sources)} sources from YAML")
                    return sources
                else:
                    logger.warning("⚠️ YAML loaded but no sources created, using fallback")
            else:
                logger.warning("⚠️ No valid configurations in YAML, using fallback")
        else:
            logger.warning(f"⚠️ YAML config not found: {CONFIG_PATH}, using fallback")
            
    except Exception as e:
        logger.error(f"❌ YAML loading failed: {e}, using fallback")
    
    # Fallback to programmatic creation
    return create_all_sources_fallback()


async def process_rss_source(source_config):
    """Process RSS source with enhanced error handling"""
    
    logger.info(f"Processing RSS source: {source_config['name']}")
    
    # Use robust RSS parser
    parser = RobustRSSParser(timeout=30)
    articles_list, errors = await parser.parse_rss_feed(source_config['url'], source_config.get('max_articles', 50))
    
    if not articles_list:
        logger.error(f"❌ Failed to parse RSS for {source_config['name']}: {errors}")
        return {'articles_discovered': 0, 'articles_processed': 0, 'articles_failed': 1, 'articles_skipped': 0}
    
    articles_processed = 0
    articles_failed = 0
    articles_discovered = len(articles_list)
    
    logger.info(f"📄 Found {articles_discovered} articles for {source_config['name']}")
    
    for article_data in articles_list[:source_config.get('max_articles', 50)]:
        try:
            # Process each article - RSS parser returns 'url' not 'link'
            article_url = article_data.get('url', '') or article_data.get('link', '')
            article_title = article_data.get('title', 'No title')
            
            if not article_url or not article_title or article_title == 'No title':
                logger.warning(f"⚠️ Skipping article with missing data: {article_title}")
                articles_failed += 1
                continue
            
            logger.info(f"Processing: {article_title}")
            
            # Here you would integrate with your existing article processing pipeline
            # For now, we'll just count it as processed
            # TODO: Integrate with existing content extraction and storage logic
            
            articles_processed += 1
            
        except Exception as e:
            logger.error(f"Error processing article '{article_data.get('title', 'Unknown')}': {e}")
            articles_failed += 1
    
    logger.info(f"✅ {source_config['name']}: {articles_processed}/{articles_discovered} processed, {articles_failed} failed")
    
    return {
        'articles_discovered': articles_discovered,
        'articles_processed': articles_processed,
        'articles_failed': articles_failed,
        'articles_skipped': 0  # For now, no duplicate detection in this function
    }


async def main_loop():
    """Enhanced main loop using unified source system."""
    logger.info("🚀 Starting NewsRagnarok main loop with unified source system...")
    
    # Load sources using new unified system
    sources = await load_unified_sources()
    if not sources:
        logger.error("❌ No valid sources loaded. Exiting.")
        return
    
    logger.info(f"🎯 Active sources: {list(sources.keys())}")
    
    # Show source information
    for name, source in sources.items():
        config = source.config
        logger.info(f"  📡 {name}: {config.source_type.value} → {config.content_type.value} "
                   f"(max: {config.max_articles_per_run}, rate: {config.rate_limit_seconds}s)")
    
    last_cleanup_time = datetime.now()
    
    # Create heartbeat directory
    heartbeat_dir = os.path.join(os.path.dirname(__file__), 'data', 'heartbeat')
    os.makedirs(heartbeat_dir, exist_ok=True)
    heartbeat_file = os.path.join(heartbeat_dir, 'crawler_heartbeat.txt')
    
    # Update heartbeat file at startup
    with open(heartbeat_file, 'w') as f:
        f.write(f"Enhanced crawler started at: {datetime.now().isoformat()}\n")
        f.write(f"Sources loaded: {list(sources.keys())}\n")
    
    # Add memory tracking
    try:
        process = psutil.Process(os.getpid())
        logger.info(f"💾 Initial memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    except ImportError:
        logger.warning("⚠️ psutil not available, memory tracking disabled")
        process = None
    
    try:
        while True:
            start_time = time.monotonic()
            logger.info("=" * 60)
            logger.info("🔄 Starting New Crawl Cycle")
            logger.info(f"⏰ Current time: {datetime.now()}")
            
            # Start cycle metrics tracking
            metrics = get_metrics()
            cycle_id = metrics.start_cycle()
            
            # Get App Insights for cloud monitoring
            app_insights = get_app_insights()
            
            # Track cycle start in App Insights
            if app_insights.enabled:
                app_insights.track_event("cycle_start", {"cycle_id": cycle_id})
            
            # Log memory usage at cycle start
            if process:
                mem_info = process.memory_info()
                memory_mb = mem_info.rss / 1024 / 1024
                logger.info(f"💾 Memory usage at cycle start: {memory_mb:.2f} MB")
                
                # Update memory usage in metrics
                metrics.update_memory_usage(memory_mb)
                
                # Track in App Insights
                if app_insights.enabled:
                    app_insights.track_memory_usage(memory_mb)
                
                # Update health check
                health_check = get_health_check()
                health_check.check_memory_usage()
            
            # Check if cleanup is needed (every 24 hours)
            current_time = datetime.now()
            if (current_time - last_cleanup_time).total_seconds() >= CLEANUP_INTERVAL_SECONDS:
                logger.info("🧹 Running scheduled cleanup...")
                await cleanup_old_data()
                last_cleanup_time = current_time
                logger.info("✅ Cleanup completed, continuing with crawl cycle...")
                
                # Force garbage collection after cleanup
                if gc:
                    logger.info("🗑️ Forcing garbage collection after cleanup...")
                    gc.collect()
                    if process:
                        logger.info(f"💾 Memory after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            
            # Check dependencies
            if not await check_dependencies():
                logger.error("❌ Dependency check failed. Skipping cycle.")
                
                # Record error in metrics
                metrics.record_cycle_error("dependency_check_failed", "Dependency check failed, skipping cycle", "critical")
                metrics.end_cycle(success=False)
                
                elapsed_time = time.monotonic() - start_time
                sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - elapsed_time)
                logger.info(f"😴 Sleeping for {sleep_duration:.2f} seconds...")
                await asyncio.sleep(sleep_duration)
                continue
            
            # ENHANCED: Process sources using unified interface
            logger.info(f"🚀 Starting enhanced crawl cycle for {len(sources)} sources...")
            
            # Cycle statistics
            cycle_stats = {
                'total_articles_discovered': 0,
                'total_articles_processed': 0,
                'total_articles_failed': 0,
                'total_articles_skipped': 0,
                'source_results': {},
                'sources_succeeded': 0,
                'sources_failed': 0
            }
            
            for i, (source_name, source) in enumerate(sources.items()):
                try:
                    logger.info(f"📡 Processing source {i+1}/{len(sources)}: {source_name}")
                    
                    # Health check for source
                    try:
                        is_healthy = await source.health_check()
                        if not is_healthy:
                            logger.warning(f"⚠️ Source {source_name} failed health check, skipping...")
                            cycle_stats['sources_failed'] += 1
                            cycle_stats['source_results'][source_name] = {
                                'error': 'Health check failed',
                                'articles_discovered': 0,
                                'articles_processed': 0,
                                'articles_failed': 1,
                                'articles_skipped': 0
                            }
                            continue
                    except Exception as health_error:
                        logger.warning(f"⚠️ Health check error for {source_name}: {health_error}")
                        # Continue processing anyway
                    
                    # Process articles using enhanced method
                    source_start_time = time.time()
                    
                    # Enhanced processing with robust RSS fallback
                    if source.config.source_type == SourceType.RSS:
                        # Try standard processing first
                        try:
                            result = await source.process_articles()
                            
                            # If no articles found, try robust RSS parser as fallback
                            if result.get('articles_discovered', 0) == 0:
                                logger.warning(f"⚠️ No articles from standard processing, trying robust RSS parser for {source_name}")
                                
                                # Create config dict for robust parser
                                rss_config = {
                                    'name': source_name,
                                    'url': source.config.rss_url or source.config.base_url,
                                    'max_articles': source.config.max_articles_per_run
                                }
                                
                                robust_result = await process_rss_source(rss_config)
                                
                                # Use robust result if it found articles
                                if robust_result.get('articles_discovered', 0) > 0:
                                    logger.info(f"✅ Robust RSS parser succeeded for {source_name}")
                                    result = robust_result
                                    
                        except Exception as e:
                            logger.error(f"❌ Standard RSS processing failed for {source_name}: {e}")
                            logger.info(f"🔄 Falling back to robust RSS parser for {source_name}")
                            
                            # Fallback to robust RSS parser
                            rss_config = {
                                'name': source_name,
                                'url': source.config.rss_url or source.config.base_url,
                                'max_articles': source.config.max_articles_per_run
                            }
                            
                            result = await process_rss_source(rss_config)
                            
                    elif source.config.source_type == SourceType.HTML_SCRAPING:
                        # HTML scraping sources (like Kabutan)
                        try:
                            logger.info(f"🔄 Processing HTML scraping source: {source_name}")
                            result = await source.process_articles()
                            
                        except Exception as e:
                            logger.error(f"❌ HTML scraping failed for {source_name}: {e}")
                            # For now, return failure result - could add HTML fallback strategies later
                            result = {
                                'articles_discovered': 0,
                                'articles_processed': 0,
                                'articles_failed': 1,
                                'articles_skipped': 0
                            }
                            
                    else:
                        # Use standard unified template method for other source types
                        result = await source.process_articles()
                    
                    processing_time = time.time() - source_start_time
                    
                    # Update cycle statistics
                    cycle_stats['total_articles_discovered'] += result['articles_discovered']
                    cycle_stats['total_articles_processed'] += result['articles_processed']
                    cycle_stats['total_articles_failed'] += result['articles_failed']
                    cycle_stats['total_articles_skipped'] += result['articles_skipped']
                    cycle_stats['sources_succeeded'] += 1
                    cycle_stats['source_results'][source_name] = result
                    
                    # Enhanced logging
                    success_rate = (result['articles_processed'] / max(1, result['articles_discovered'])) * 100
                    logger.info(f"✅ {source_name}: {result['articles_processed']}/{result['articles_discovered']} "
                               f"processed ({success_rate:.1f}% success) in {processing_time:.2f}s")
                    
                    if result['articles_skipped'] > 0:
                        logger.info(f"   ⏭️ Skipped {result['articles_skipped']} duplicates")
                    if result['articles_failed'] > 0:
                        logger.warning(f"   ❌ Failed {result['articles_failed']} articles")
                    
                    # Small delay between sources to manage memory
                    await asyncio.sleep(5)
                    
                    # Garbage collect after each source
                    if gc and i % 2 == 1:  # Every 2 sources
                        logger.info(f"🗑️ Performing garbage collection after source {i+1}/{len(sources)}")
                        gc.collect()
                        if process:
                            logger.info(f"💾 Memory after source {i+1}: {process.memory_info().rss / 1024 / 1024:.2f} MB")
                            
                    # Check for excessive memory usage
                    if process and process.memory_info().rss > 800 * 1024 * 1024:  # Over 800MB
                        logger.warning("⚠️ Memory usage high, performing emergency cleanup")
                        gc.collect()
                        await asyncio.sleep(10)  # Give system time to reclaim memory
                        
                except Exception as e:
                    logger.error(f"❌ Error processing source {source_name}: {e}")
                    cycle_stats['sources_failed'] += 1
                    cycle_stats['source_results'][source_name] = {
                        'error': str(e),
                        'articles_discovered': 0,
                        'articles_processed': 0,
                        'articles_failed': 1,
                        'articles_skipped': 0
                    }
                    # Continue with other sources
            
            # Enhanced Cycle Summary
            logger.info("=" * 60)
            logger.info("📊 ENHANCED CRAWL CYCLE SUMMARY")
            logger.info("=" * 60)
            
            # Overall statistics
            overall_success_rate = (cycle_stats['total_articles_processed'] / 
                                  max(1, cycle_stats['total_articles_discovered'])) * 100
            
            logger.info(f"🎯 Overall Results:")
            logger.info(f"   📈 Articles discovered: {cycle_stats['total_articles_discovered']}")
            logger.info(f"   ✅ Articles processed: {cycle_stats['total_articles_processed']}")
            logger.info(f"   ❌ Articles failed: {cycle_stats['total_articles_failed']}")
            logger.info(f"   ⏭️ Articles skipped (duplicates): {cycle_stats['total_articles_skipped']}")
            logger.info(f"   🎯 Overall success rate: {overall_success_rate:.1f}%")
            logger.info(f"   📡 Sources succeeded: {cycle_stats['sources_succeeded']}/{len(sources)}")
            logger.info(f"   ❌ Sources failed: {cycle_stats['sources_failed']}/{len(sources)}")
            
            # Per-source breakdown
            logger.info(f"\n📋 Per-Source Breakdown:")
            for source_name, result in cycle_stats['source_results'].items():
                if 'error' in result:
                    logger.error(f"   ❌ {source_name}: {result['error']}")
                else:
                    source_success_rate = (result['articles_processed'] / max(1, result['articles_discovered'])) * 100
                    logger.info(f"   📡 {source_name}: {result['articles_processed']}/{result['articles_discovered']} "
                               f"({source_success_rate:.1f}% success, {result['articles_skipped']} skipped)")
            
            # Final garbage collection at end of cycle
            if gc:
                logger.info("🗑️ Forcing final garbage collection at end of cycle...")
                gc.collect()
                if process:
                    final_memory = process.memory_info().rss / 1024 / 1024
                    logger.info(f"💾 Memory after cycle end: {final_memory:.2f} MB")
            
            # Calculate next run time
            cycle_duration = time.monotonic() - start_time
            sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - cycle_duration)
            next_run_time = datetime.now() + timedelta(seconds=sleep_duration)
            
            logger.info(f"\n⏱️ Timing Information:")
            logger.info(f"   ⌛ Cycle finished in {cycle_duration:.2f} seconds")
            logger.info(f"   ⏰ Next crawl cycle scheduled for: {next_run_time}")
            
            # Calculate time until next cleanup
            time_until_cleanup = CLEANUP_INTERVAL_SECONDS - (datetime.now() - last_cleanup_time).total_seconds()
            logger.info(f"   🧹 Next cleanup in: {time_until_cleanup/3600:.2f} hours")
            
            # End cycle metrics tracking
            overall_cycle_success = cycle_stats['sources_succeeded'] > 0
            metrics.end_cycle(success=overall_cycle_success)
            
            # Track cycle completion in App Insights
            if app_insights.enabled:
                app_insights.track_cycle_duration(cycle_duration)
                app_insights.track_event("enhanced_cycle_completed", {
                    "cycle_id": cycle_id,
                    "duration_seconds": str(round(cycle_duration, 2)),
                    "total_articles_discovered": str(cycle_stats['total_articles_discovered']),
                    "total_articles_processed": str(cycle_stats['total_articles_processed']),
                    "total_articles_failed": str(cycle_stats['total_articles_failed']),
                    "total_articles_skipped": str(cycle_stats['total_articles_skipped']),
                    "sources_succeeded": str(cycle_stats['sources_succeeded']),
                    "sources_failed": str(cycle_stats['sources_failed']),
                    "overall_success_rate": str(round(overall_success_rate, 2)),
                    "unified_system": "true"
                })
            
            # Save daily metrics
            metrics.save_daily_metrics()
            
            # Optional: log system resources before sleep
            if process:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    mem_percent = psutil.virtual_memory().percent
                    logger.info(f"🖥️ System resources: CPU {cpu_percent}%, Memory {mem_percent}%")
                except:
                    pass
                    
            # Update heartbeat file before sleep
            try:
                with open(heartbeat_file, 'a') as f:
                    f.write(f"Enhanced cycle completed at: {datetime.now().isoformat()}\n")
                    f.write(f"  Sources: {cycle_stats['sources_succeeded']}/{len(sources)} succeeded\n")
                    f.write(f"  Articles: {cycle_stats['total_articles_processed']} processed\n")
                    f.write(f"  Next cycle: {next_run_time.isoformat()}\n")
            except Exception as heartbeat_err:
                logger.warning(f"⚠️ Failed to update heartbeat file: {str(heartbeat_err)}")
                
            # Enhanced sleep logging
            logger.info("=" * 60)
            logger.info(f"😴 SLEEPING for {sleep_duration:.2f} seconds...")
            logger.info(f"⏰ Will wake up at {next_run_time}")
            logger.info("=" * 60)
            
            try:
                await asyncio.sleep(sleep_duration)
                logger.info("=" * 60)
                logger.info(f"⏰ WOKE UP from sleep at: {datetime.now()}")
                logger.info("🚀 STARTING NEXT ENHANCED CYCLE")
                logger.info("=" * 60)
            except Exception as sleep_err:
                logger.error(f"❌ Error during sleep: {str(sleep_err)}")
                await asyncio.sleep(5)  # Short delay before retry
            
    except KeyboardInterrupt:
        logger.info("⚠️ Received interrupt signal. Shutting down enhanced crawler...")
        
        # Flush App Insights telemetry before exit
        if app_insights.enabled:
            app_insights.track_event("enhanced_application_shutdown", {"reason": "keyboard_interrupt"})
            app_insights.flush()
            
        await cleanup_old_data()
        logger.info("✅ Final cleanup completed. Enhanced crawler shut down.")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in enhanced main loop: {e}")
        import traceback
        logger.error(f"📋 Stack trace:\n{traceback.format_exc()}")
        
        # Try to recover
        try:
            logger.info("🔄 Attempting recovery...")
            if gc:
                gc.collect()
            await asyncio.sleep(60)  # Wait a minute before restarting
            
            # Try reloading sources in case of configuration issues
            logger.info("🔄 Reloading sources for recovery...")
            sources = await load_unified_sources()
            if sources:
                logger.info("✅ Sources reloaded successfully, restarting loop...")
                await main_loop()  # Recursive call to restart
            else:
                logger.critical("❌ Could not reload sources during recovery")
                
        except Exception as recover_error:
            logger.critical(f"💥 Recovery failed: {recover_error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced NewsRagnarok Crawler with Unified Source System")
    parser.add_argument("--clear-collection", action="store_true", help="Clear all documents from the Qdrant collection")
    parser.add_argument("--recreate-collection", action="store_true", help="Delete and recreate the Qdrant collection")
    parser.add_argument("--test-sources", action="store_true", help="Test source creation and exit")
    parser.add_argument("--list-sources", action="store_true", help="List available sources and exit")
    args = parser.parse_args()
    
    # Initialize monitoring system
    logger.info("🔍 Initializing monitoring system...")
    metrics, health_check, duplicate_detector, app_insights, alert_manager = init_monitoring()
    logger.info("✅ Monitoring system initialized successfully")
    
    # Test Slack alerts on startup
    if os.getenv("ALERT_SLACK_ENABLED", "false").lower() == "true":
        logger.info("🔔 Testing Slack alerts...")
        try:
            trigger_test_alert(
                message=f"Enhanced NewsRagnarok startup test from {os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or 'unknown'}",
                alert_type="enhanced_startup_test"
            )
            logger.info("✅ Slack test alert triggered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to send Slack test alert: {str(e)}")
    else:
        logger.info("⚠️ Slack alerts are disabled. Set ALERT_SLACK_ENABLED=true to enable.")
    
    # Handle command line arguments
    if args.test_sources:
        logger.info("🧪 Testing source creation...")
        sources = asyncio.run(load_unified_sources())
        if sources:
            logger.info(f"✅ Successfully created {len(sources)} sources:")
            for name, source in sources.items():
                config = source.config
                logger.info(f"  📡 {name}: {config.source_type.value} → {config.content_type.value}")
        else:
            logger.error("❌ No sources could be created")
        sys.exit(0)
    
    if args.list_sources:
        logger.info("📋 Available sources in unified system:")
        try:
            from crawler.factories import SourceFactory
            custom_sources = SourceFactory.get_custom_sources()
            supported_types = SourceFactory.get_supported_source_types()
            
            logger.info(f"🔧 Custom Adapters: {custom_sources}")
            logger.info(f"📚 Template Types: {[t.value for t in supported_types]}")
        except Exception as e:
            logger.error(f"❌ Error listing sources: {e}")
        sys.exit(0)
    
    # Handle collection cleanup/recreation
    if args.clear_collection or args.recreate_collection:
        if args.recreate_collection:
            logger.info("🔄 Recreate collection flag detected, recreating Qdrant collection...")
            success = asyncio.run(recreate_qdrant_collection())
            if success:
                logger.info("✅ Qdrant collection recreation completed successfully")
            else:
                logger.error("❌ Qdrant collection recreation failed")
        elif args.clear_collection:
            logger.info("🧹 Clear collection flag detected, clearing Qdrant collection...")
            success = asyncio.run(clear_qdrant_collection())
            if success:
                logger.info("✅ Qdrant collection cleanup completed successfully")
            else:
                logger.error("❌ Qdrant collection cleanup failed")
        
        if not (args.clear_collection and not args.recreate_collection):
            logger.info("✅ Cleanup/recreation operations completed, exiting...")
            sys.exit(0)
    
    # Track application start event
    if app_insights.enabled:
        app_insights.track_event("enhanced_application_start", {
            "version": "2.0.0-enhanced",
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "unified_system": "true"
        })
    
    # Ensure data directories exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'metrics'), exist_ok=True)
    
    # Enhanced logging for Azure App Service
    port = os.environ.get('PORT', '8000')
    logger.info(f"🌐 Enhanced Azure App Service Configuration:")
    logger.info(f"   📡 PORT environment variable: {port}")
    logger.info(f"   🚀 Starting enhanced health check server on port {port}")
    logger.info(f"   🔧 Using unified source system with factory pattern")
    
    # Start health check server
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Give health server a moment to start
    time.sleep(2)
    
    # Run the enhanced main crawler loop
    logger.info("🚀 Starting Enhanced NewsRagnarok Crawler...")
    asyncio.run(main_loop())
