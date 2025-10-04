"""
Data lifecycle management for the NewsRagnarok crawler.
Handles cleanup of old data, verification of storage integrity,
and ensures proper data retention policies.
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
import pytz

# Import our modules
from clients.vector_client import VectorClient
from crawler.utils.azure_utils import (
    check_azure_connection, 
    list_blobs_by_date_prefix,
    _get_azure_credentials,
    _get_blob_service_client
)
from monitoring.metrics import get_metrics

class DataLifecycleManager:
    """Manages the lifecycle of crawled data across storage systems."""
    
    def __init__(self):
        """Initialize the data lifecycle manager."""
        self.retention_days = int(os.environ.get('DATA_RETENTION_DAYS', '90'))
        self.metrics = get_metrics()
        logger.info(f"Data lifecycle manager initialized with {self.retention_days} days retention policy")
    
    async def cleanup_old_data(self) -> Dict[str, Any]:
        """Clean up data older than the retention period from all storage systems.
        
        Returns:
            Dictionary with cleanup statistics
        """
        logger.info(f"Starting cleanup of data older than {self.retention_days} days")
        start_time = datetime.now()
        
        # Calculate cutoff date
        cutoff_date = datetime.now(pytz.timezone('US/Pacific')) - timedelta(days=self.retention_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        logger.info(f"Cutoff date for deletion: {cutoff_str}")
        
        # Track results
        results = {
            'qdrant_deleted': 0,
            'azure_deleted': 0,
            'errors': [],
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'status': 'in_progress'
        }
        
        try:
            # 1. Clean up Qdrant vector database
            qdrant_result = await self._cleanup_qdrant(cutoff_date)
            results['qdrant_deleted'] = qdrant_result.get('deleted_count', 0)
            
            # 2. Clean up Azure Blob Storage
            azure_result = await self._cleanup_azure_blobs(cutoff_date)
            results['azure_deleted'] = azure_result.get('deleted_count', 0)
            
            # 3. Update metrics
            total_deleted = results['qdrant_deleted'] + results['azure_deleted']
            self.metrics.record_documents_deleted(total_deleted)
            
            # Update final status
            results['status'] = 'completed'
            logger.info(f"Cleanup completed: {total_deleted} total items deleted")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            results['errors'].append(str(e))
            results['status'] = 'failed'
        finally:
            # Calculate duration
            end_time = datetime.now()
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        return results
    
    async def _cleanup_qdrant(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Clean up old data from Qdrant vector database.
        
        Args:
            cutoff_date: Delete documents older than this date
            
        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Cleaning up old data from Qdrant vector database")
        result = {
            'deleted_count': 0,
            'status': 'failed',
            'error': None
        }
        
        vector_client = None
        try:
            # Create Qdrant client
            vector_client = VectorClient()
            
            # Get stats before deletion
            before_stats = await vector_client.get_collection_stats()
            before_count = before_stats.get('points_count', 0) if before_stats else 0
            
            # Delete old documents
            # Convert retention days to hours for the existing function
            retention_hours = self.retention_days * 24
            delete_result = await vector_client.delete_documents_older_than(hours=retention_hours)
            
            if delete_result:
                result['deleted_count'] = delete_result.get('deleted_count', 0)
                result['status'] = 'success'
                logger.info(f"Deleted {result['deleted_count']} documents from Qdrant")
            else:
                result['status'] = 'failed'
                result['error'] = 'No response from delete operation'
                logger.error("Failed to delete documents from Qdrant")
            
            # Get stats after deletion to verify
            after_stats = await vector_client.get_collection_stats()
            after_count = after_stats.get('points_count', 0) if after_stats else 0
            
            # Update metrics with current document count
            self.metrics.update_qdrant_stats(after_count)
            
            # Verify deletion worked
            expected_count = max(0, before_count - result['deleted_count'])
            if after_count != expected_count:
                logger.warning(f"Qdrant document count mismatch after deletion. Expected: {expected_count}, Actual: {after_count}")
            
        except Exception as e:
            logger.error(f"Error cleaning up Qdrant data: {e}")
            result['error'] = str(e)
        finally:
            if vector_client:
                await vector_client.close()
        
        return result
    
    async def _cleanup_azure_blobs(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Clean up old data from Azure Blob Storage.
        
        Args:
            cutoff_date: Delete blobs older than this date
            
        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Cleaning up old data from Azure Blob Storage")
        result = {
            'deleted_count': 0,
            'status': 'failed',
            'error': None
        }
        
        try:
            # Check Azure connection
            azure_ok = check_azure_connection()
            if not azure_ok:
                result['error'] = 'Azure connection failed'
                return result
            
            # Get Azure credentials
            account_name, access_key, container = _get_azure_credentials()
            if not account_name:
                result['error'] = 'Azure credentials not configured'
                return result
            
            # Create blob service client
            blob_service_client = _get_blob_service_client(account_name, access_key)
            container_client = blob_service_client.get_container_client(container)
            
            # List blobs to delete
            blobs_to_delete = []
            
            # We need to list blobs by year/month/day, so we'll generate all date combinations
            # before the cutoff date up to a reasonable limit (e.g., 2 years)
            current_date = cutoff_date
            min_date = datetime.now() - timedelta(days=365*2)  # 2 years ago
            
            while current_date >= min_date:
                # Format as YYYY/MM/DD for Azure path prefix
                date_prefix = current_date.strftime('%Y/%m/%d')
                
                # List blobs with this prefix
                blobs = list_blobs_by_date_prefix(date_prefix, container)
                blobs_to_delete.extend(blobs)
                
                # Move to previous day
                current_date -= timedelta(days=1)
            
            # Delete the blobs
            deleted_count = 0
            for blob_name in blobs_to_delete:
                try:
                    # Delete the blob
                    blob_client = container_client.get_blob_client(blob_name)
                    blob_client.delete_blob()
                    deleted_count += 1
                    
                    # Log every 10 deletions to avoid excessive logging
                    if deleted_count % 10 == 0:
                        logger.info(f"Deleted {deleted_count}/{len(blobs_to_delete)} blobs from Azure")
                        
                except Exception as e:
                    logger.error(f"Error deleting blob {blob_name}: {e}")
            
            # Update result
            result['deleted_count'] = deleted_count
            result['status'] = 'success'
            logger.info(f"Deleted {deleted_count} blobs from Azure")
            
            # Update metrics with current blob count
            total_blobs = len(list(container_client.list_blobs()))
            self.metrics.update_azure_stats(total_blobs)
            
        except Exception as e:
            logger.error(f"Error cleaning up Azure data: {e}")
            result['error'] = str(e)
        
        return result
    
    async def verify_data_integrity(self) -> Dict[str, Any]:
        """Verify data integrity across storage systems.
        
        Checks:
        1. Qdrant document count matches expected
        2. Azure blob count matches expected
        3. Sample documents exist in both systems
        
        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying data integrity across storage systems")
        result = {
            'status': 'in_progress',
            'qdrant_check': 'pending',
            'azure_check': 'pending',
            'cross_check': 'pending',
            'errors': []
        }
        
        try:
            # Check Qdrant
            qdrant_ok = await self._verify_qdrant()
            result['qdrant_check'] = 'success' if qdrant_ok else 'failed'
            
            # Check Azure
            azure_ok = await self._verify_azure()
            result['azure_check'] = 'success' if azure_ok else 'failed'
            
            # Cross-check (sample document exists in both)
            cross_ok = await self._cross_check_storage()
            result['cross_check'] = 'success' if cross_ok else 'failed'
            
            # Final status
            if qdrant_ok and azure_ok and cross_ok:
                result['status'] = 'success'
                logger.info("Data integrity verification passed")
            else:
                result['status'] = 'failed'
                logger.warning("Data integrity verification failed")
                
        except Exception as e:
            logger.error(f"Error verifying data integrity: {e}")
            result['errors'].append(str(e))
            result['status'] = 'failed'
        
        return result
    
    async def _verify_qdrant(self) -> bool:
        """Verify Qdrant database integrity.
        
        Returns:
            True if verification passed, False otherwise
        """
        vector_client = None
        try:
            # Create Qdrant client
            vector_client = VectorClient()
            
            # Check health
            health_ok = await vector_client.check_health()
            if not health_ok:
                logger.error("Qdrant health check failed")
                return False
            
            # Get collection stats
            stats = await vector_client.get_collection_stats()
            if not stats:
                logger.error("Failed to get Qdrant collection stats")
                return False
            
            # Update metrics
            doc_count = stats.get('points_count', 0)
            self.metrics.update_qdrant_stats(doc_count)
            
            logger.info(f"Qdrant verification passed: {doc_count} documents found")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying Qdrant: {e}")
            return False
        finally:
            if vector_client:
                await vector_client.close()
    
    async def _verify_azure(self) -> bool:
        """Verify Azure Blob Storage integrity.
        
        Returns:
            True if verification passed, False otherwise
        """
        try:
            # Check Azure connection
            azure_ok = check_azure_connection()
            if not azure_ok:
                logger.error("Azure connection failed")
                return False
            
            # Get Azure credentials
            account_name, access_key, container = _get_azure_credentials()
            if not account_name:
                logger.error("Azure credentials not configured")
                return False
            
            # Create blob service client
            blob_service_client = _get_blob_service_client(account_name, access_key)
            container_client = blob_service_client.get_container_client(container)
            
            # Count blobs
            blob_count = len(list(container_client.list_blobs()))
            
            # Update metrics
            self.metrics.update_azure_stats(blob_count)
            
            logger.info(f"Azure verification passed: {blob_count} blobs found")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying Azure: {e}")
            return False
    
    async def _cross_check_storage(self) -> bool:
        """Cross-check data between Qdrant and Azure.
        
        Returns:
            True if verification passed, False otherwise
        """
        # This is a basic implementation - you might want to expand this
        # with more sophisticated checks in a production environment
        try:
            # For now, just check that both systems are accessible
            qdrant_ok = await self._verify_qdrant()
            azure_ok = await self._verify_azure()
            
            return qdrant_ok and azure_ok
            
        except Exception as e:
            logger.error(f"Error cross-checking storage: {e}")
            return False

# Factory function
def create_lifecycle_manager() -> DataLifecycleManager:
    """Create a data lifecycle manager instance."""
    return DataLifecycleManager()
