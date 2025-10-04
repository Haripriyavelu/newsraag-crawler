"""
Manages the Qdrant index, including cleanup of old documents.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

from clients.vector_client import VectorClient
# Import Azure utils
from crawler.utils.azure_utils import download_json_from_azure, construct_blob_path

async def cleanup_old_documents(hours_threshold: int = 24):
    """Removes documents older than the specified threshold from the Qdrant index.

    This implementation fetches all document statuses, identifies documents older than
    the threshold based on their 'created_at' or 'updated_at' timestamp, clears
    the entire index, and (TODO) re-inserts the documents that should be kept.

    Args:
        hours_threshold: The maximum age of documents (in hours) to keep.
    """
    logger.info(f"Starting cleanup of documents older than {hours_threshold} hours...")
    client = None
    docs_to_keep_info = {} # Store full doc info for re-insertion {doc_id: doc_dict}
    total_docs_before = 0
    kept_count = 0
    deleted_count = 0

    try:
        client = VectorClient()
        if not await client.check_health():
            logger.error("Vector service API is not healthy. Aborting cleanup.")
            return

        # 1. Get all current document statuses
        logger.info("Querying all document statuses...")
        all_docs = await client.query_documents()
        if all_docs is None:
            logger.error("Failed to query documents. Aborting cleanup.")
            return
        
        total_docs_before = len(all_docs)
        logger.info(f"Found {total_docs_before} documents in the index.")
        if total_docs_before == 0:
            logger.info("No documents in index. Cleanup not needed.")
            return

        # 2. Identify documents to keep vs delete
        cutoff_time_utc = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
        logger.info(f"Identifying documents created/updated after cutoff: {cutoff_time_utc.isoformat()}")

        docs_to_keep_info = {} # Store full doc info for re-insertion {doc_id: doc_dict}
        doc_ids_to_delete = set()

        for doc in all_docs:
            doc_id = doc.get('id')
            timestamp_str = doc.get('updated_at') or doc.get('created_at')
            file_path_base = doc.get('file_path', 'unknown_source') # Base filename part

            if not doc_id or not timestamp_str:
                logger.warning(f"Skipping doc {doc_id or 'Unknown ID'} due to missing ID or timestamp.")
                continue

            try:
                doc_dt = datetime.fromisoformat(timestamp_str)
                if doc_dt.tzinfo is None:
                    doc_dt = doc_dt.replace(tzinfo=timezone.utc)
                else:
                    doc_dt = doc_dt.astimezone(timezone.utc)

                if doc_dt >= cutoff_time_utc:
                    docs_to_keep_info[doc_id] = doc # Store the whole doc dict
                else:
                    doc_ids_to_delete.add(doc_id)

            except ValueError:
                logger.warning(f"Could not parse timestamp '{timestamp_str}' for doc {doc_id}. Assuming it should be deleted.")
                doc_ids_to_delete.add(doc_id)
            except Exception as e:
                 logger.error(f"Error processing timestamp for doc {doc_id}: {e}. Assuming it should be deleted.")
                 doc_ids_to_delete.add(doc_id)
        
        actual_kept_count = len(docs_to_keep_info)
        actual_deleted_count = total_docs_before - actual_kept_count
        logger.info(f"Identified {actual_kept_count} documents to keep and {actual_deleted_count} documents to delete.")

        if not doc_ids_to_delete:
            logger.info("No documents older than threshold found. No cleanup action needed.")
            return

        # --- Step 3: Fetch content for documents to keep --- 
        docs_to_reinsert = [] # List of (content, metadata) tuples
        logger.info(f"Fetching content for {len(docs_to_keep_info)} documents to keep...")
        for doc_id, doc_info in docs_to_keep_info.items():
           base_filename = doc_info.get('file_path')
           # Need the original publish date (PST) to construct the correct path
           # Let's try parsing it from the metadata WE HOPE is there now, or use created_at/updated_at as fallback
           original_metadata = doc_info.get('metadata', {})
           publish_date_pst_str = original_metadata.get('publishDatePst')
           publish_date_pst = None
           if publish_date_pst_str:
                try:
                    publish_date_pst = datetime.fromisoformat(publish_date_pst_str)
                except ValueError:
                     logger.warning(f"Could not parse stored publishDatePst '{publish_date_pst_str}' for {doc_id}")
           
           # Fallback to using created_at/updated_at if publishDatePst not found/parsed
           if not publish_date_pst:
                timestamp_str = doc_info.get('updated_at') or doc_info.get('created_at')
                if timestamp_str:
                    try:
                        # Assume created_at/updated_at are UTC, need to convert to PST for path?
                        # Or maybe _get_blob_path handles UTC? Let's assume it needs PST.
                        # This is getting complex - requires time_utils. Let's simplify for now:
                        # Use the date part directly from the timestamp string if possible.
                        fallback_dt = datetime.fromisoformat(timestamp_str)
                        # _get_blob_path expects datetime object, let's pass it
                        publish_date_pst = fallback_dt # Pass UTC/original timestamp, path logic might handle it
                        logger.warning(f"Using fallback timestamp {timestamp_str} to construct path for {doc_id}")
                    except ValueError:
                        logger.error(f"Could not parse fallback timestamp {timestamp_str} for {doc_id}")
                        continue # Cannot determine path

           if base_filename and base_filename != 'unknown_source' and publish_date_pst:
               # Construct the full path using the helper
               blob_path = construct_blob_path(base_filename, publish_date_pst)
               try:
                   logger.debug(f"Attempting to download content from: {blob_path}")
                   content_dict = await download_json_from_azure(blob_path)
                   if content_dict and 'content' in content_dict:
                        # Extract content and potentially recreate metadata for re-insertion
                        # The downloaded dict IS the original data structure
                        content = content_dict.get('content')
                        # Prepare metadata for re-insertion
                        metadata_to_resend = {
                             "publishDatePst": content_dict.get('publishDatePst'), # Already string? Assume yes
                             "source": content_dict.get("_source"),
                             "author": content_dict.get("_author"),
                             "category": content_dict.get("_category"),
                             "article_id": content_dict.get("_article_id")
                        }
                        metadata_to_resend = {k: v for k, v in metadata_to_resend.items() if v is not None}
                        docs_to_reinsert.append((content, metadata_to_resend))
                   else:
                        logger.warning(f"Could not retrieve valid content structure for doc {doc_id} from blob {blob_path}")
               except Exception as fetch_err:
                   logger.error(f"Error fetching content for doc {doc_id} from blob {blob_path}: {fetch_err}")
           else:
               logger.warning(f"Cannot determine filename/date to fetch content for doc {doc_id}")

        # --- Step 4: Clear entire index --- 
        logger.info("Attempting to clear the Qdrant index...")
        clear_result = await client.clear_all_documents()
        if not clear_result or clear_result.get('status') != 'success':
             logger.error(f"Failed to clear Qdrant index. Aborting re-insertion. Message: {clear_result.get('message') if clear_result else 'N/A'}")
             return
        logger.info("Successfully cleared Qdrant index.")

        # --- Step 5: Re-insert kept documents --- 
        re_inserted_count = 0
        failed_reinsert_count = 0
        if docs_to_reinsert:
           logger.info(f"Re-inserting {len(docs_to_reinsert)} documents...")
           # Consider batching if API supports /texts with metadata
           insert_tasks = []
           for content, metadata in docs_to_reinsert:
                insert_tasks.append(client.add_document(content, metadata=metadata))
           
           results = await asyncio.gather(*insert_tasks)
           for result in results:
                if result and result.get('status') == 'success':
                    re_inserted_count += 1
                else:
                    logger.warning(f"Failed to re-insert document. Response: {result}")
                    failed_reinsert_count += 1
                    
           logger.info(f"Re-insertion complete. Success: {re_inserted_count}, Failed: {failed_reinsert_count}")
        else:
            logger.info("No document content was retrieved/prepared for re-insertion.")

        logger.info(f"Cleanup task finished. Documents evaluated: {total_docs_before}, Kept: {actual_kept_count}, Deleted (Cleared): {actual_deleted_count}, Re-inserted: {re_inserted_count}")

    except ValueError as ve: # Catch client init error
         logger.error(f"Qdrant client init failed: {ve}")
    except Exception as e:
        logger.error(f"An error occurred during document cleanup: {e}", exc_info=True)
    finally:
        if client:
            await client.close()
            logger.info("Qdrant client closed.")

# Example usage (for testing)
# async def main():
#     await cleanup_old_documents(hours_threshold=24)
# 
# if __name__ == "__main__":
#     asyncio.run(main()) 