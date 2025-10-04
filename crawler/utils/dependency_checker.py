"""
Dependency checker for NewsRagnarok Crawler.
"""
import os
import time
import asyncio
import sys
import os
from loguru import logger

# Simple fix: add project root to path if not there
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from clients.vector_client import VectorClient
from monitoring.health_check import get_health_check
from monitoring.app_insights import get_app_insights
from .azure_utils import check_azure_connection

async def check_dependencies() -> bool:
    """
    Check if all dependencies are available.
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    logger.info("Checking dependencies...")
    health_check = get_health_check()
    
    # Get App Insights for monitoring
    app_insights = get_app_insights()
    
    # Check Redis (optional for now)
    redis_ok = True  # We'll implement this later if needed
    health_check.update_dependency_status("redis", redis_ok)
    if app_insights.enabled:
        app_insights.track_dependency_status("redis", redis_ok)
    
    # Check Qdrant
    vector_client = None
    try:
        start_time = time.time()
        vector_client = VectorClient()
        vector_ok = await vector_client.check_health()
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(f"- Qdrant vector service connection: {'OK' if vector_ok else 'FAILED'}")
        health_check.update_dependency_status("qdrant", vector_ok)
        
        # Track in App Insights
        if app_insights.enabled:
            app_insights.track_dependency_status("qdrant", vector_ok, duration_ms)
    except Exception as e:
        logger.error(f"- Qdrant vector service connection: FAILED ({e})")
        vector_ok = False
        health_check.update_dependency_status("qdrant", False, str(e))
        
        # Track failure in App Insights
        if app_insights.enabled:
            app_insights.track_dependency_status("qdrant", False)
            app_insights.track_exception(e, {"dependency": "qdrant"})
    finally:
        if vector_client:
            await vector_client.close()
    
    # Check Azure
    start_time = time.time()
    azure_ok = check_azure_connection()
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(f"- Azure Blob Storage connection: {'OK' if azure_ok else 'FAILED'}")
    health_check.update_dependency_status("azure", azure_ok)
    
    # Track in App Insights
    if app_insights.enabled:
        app_insights.track_dependency_status("azure_blob", azure_ok, duration_ms)
    
    # Check OpenAI API by simply checking if keys are set
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_ok = openai_api_key is not None
    logger.info(f"- OpenAI API credentials: {'OK' if openai_ok else 'MISSING'}")
    health_check.update_dependency_status("openai", openai_ok)
    
    # Track in App Insights
    if app_insights.enabled:
        app_insights.track_dependency_status("openai", openai_ok)
    
    # Return overall status
    return redis_ok and vector_ok and azure_ok
