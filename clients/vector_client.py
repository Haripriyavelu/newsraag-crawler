import os
import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VectorClient:
    """Unified client for vector database operations using Qdrant."""
    
    def __init__(self):
        """Initialize the Qdrant vector client."""
        from .qdrant_client import QdrantClientWrapper
        self.client = QdrantClientWrapper()
        self.backend = "qdrant"  # Keep for compatibility
        logger.info("Initialized Qdrant vector client")

    async def close(self):
        """Close the vector client."""
        if self.client:
            await self.client.close()

    async def check_health(self) -> bool:
        """Check the health of the vector service."""
        try:
            return await self.client.check_health()
        except Exception as e:
            logger.error(f"Health check failed for Qdrant: {e}")
            return False

    async def add_document(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Add a document to the vector database with retry mechanism."""
        # Retry configuration
        max_retries = 3
        retry_delay_base = 2  # seconds
        
        for attempt in range(max_retries):
            # Calculate retry delay OUTSIDE try block to avoid scope issues
            retry_delay = retry_delay_base ** attempt if attempt > 0 else 0
            
            try:
                if not text_content or len(text_content.strip()) < 50:
                    logger.warning(f"Text content too short or empty: {len(text_content if text_content else '')} chars")
                    return {
                        "status": "error",
                        "message": "Text content too short or empty"
                    }
                
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{max_retries} after {retry_delay}s delay")
                    await asyncio.sleep(retry_delay)
                    
                logger.info(f"Adding document to Qdrant (content length: {len(text_content)} chars)")
                result = await self.client.add_document(text_content, metadata)
                
                if result:
                    logger.info(f"Successfully added document to Qdrant: {result.get('document_id', 'unknown ID')}")
                    # Successful operation - return result
                    return result
                else:
                    # If we get None but no exception, log and retry
                    logger.warning(f"Empty result from Qdrant (attempt {attempt+1}/{max_retries})")
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # Final attempt failed - record error and alert
                        logger.error("Failed to add document to Qdrant after all retries: received None result")
                        
                        # Try to record a specific Qdrant error with alert
                        try:
                            from monitoring.metrics import get_metrics
                            metrics = get_metrics()
                            article_title = metadata.get('title', 'Unknown') if metadata else 'Unknown'
                            metrics.record_qdrant_error(
                                "Failed to add document to Qdrant after all retries: timeout parameter error", 
                                article_title, 
                                "error"
                            )
                        except Exception as alert_error:
                            logger.error(f"Failed to record Qdrant error: {alert_error}")
                        
                        return None
                        
            except Exception as e:
                # Log the error with attempt information
                logger.error(f"Error adding document to Qdrant (attempt {attempt+1}/{max_retries}): {str(e)}")
                
                # If we have retries left, wait and try again
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # All retries exhausted
                    import traceback
                    logger.error(f"All retries failed. Stack trace: {traceback.format_exc()}")
                    
                    # Try to record a specific Qdrant error with alert
                    try:
                        from monitoring.metrics import get_metrics
                        metrics = get_metrics()
                        article_title = metadata.get('title', 'Unknown') if metadata else 'Unknown'
                        metrics.record_qdrant_error(
                            f"Failed to add document to Qdrant after all retries: {str(e)}", 
                            article_title, 
                            "error"
                        )
                    except Exception as alert_error:
                        logger.error(f"Failed to record Qdrant error: {alert_error}")
                    
                    return None
        
        # This shouldn't be reached, but just in case
        logger.error("Failed to add document to Qdrant: exhausted all retries")
        return None

    async def search_documents(self, query: str, limit: int = 10, score_threshold: float = 0.3) -> Optional[List[Dict[str, Any]]]:
        """Search for documents similar to the query."""
        try:
            if not query or len(query.strip()) < 2:
                logger.warning(f"Query too short: '{query}'")
                return None
                
            logger.info(f"Searching for: '{query}' with threshold {score_threshold}")
            return await self.client.search_documents(query, limit, score_threshold)
        except Exception as e:
            logger.error(f"Error searching documents in Qdrant: {str(e)}")
            return None

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector database."""
        try:
            return await self.client.delete_document(document_id)
        except Exception as e:
            logger.error(f"Error deleting document from Qdrant: {e}")
            return False

    async def delete_documents_older_than(self, hours: int) -> Optional[Dict[str, Any]]:
        """Delete documents older than specified hours."""
        try:
            return await self.client.delete_documents_older_than(hours)
        except Exception as e:
            logger.error(f"Error deleting old documents from Qdrant: {e}")
            return None

    async def clear_all_documents(self) -> Optional[Dict[str, Any]]:
        """Clear all documents from the vector database."""
        try:
            return await self.client.clear_all_documents()
        except Exception as e:
            logger.error(f"Error clearing documents from Qdrant: {e}")
            return None

    async def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """Get collection statistics."""
        try:
            return await self.client.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting stats from Qdrant: {e}")
            return None

# Factory function for easy client creation
def create_vector_client() -> VectorClient:
    """Factory function to create a Qdrant vector client.
    
    Returns:
        VectorClient instance
    """
    return VectorClient()


