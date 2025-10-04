import os
import dotenv
from typing import Optional, Tuple, Dict, Any
from azure.storage.blob import BlobServiceClient, ContentSettings
from loguru import logger
from datetime import datetime
import json

dotenv.load_dotenv()

# --- Azure Credentials Helper --- 
def _get_azure_credentials():
    """Gets Azure credentials from environment variables."""
    account_name = os.environ.get('AZ_ACCOUNT_NAME')
    access_key = os.environ.get('AZ_BLOB_ACCESS_KEY')
    container = os.environ.get('AZ_CONTAINER_NAME')
    if not account_name or not access_key or not container:
        logger.error("Missing Azure Storage credentials (AZ_ACCOUNT_NAME, AZ_BLOB_ACCESS_KEY, AZ_CONTAINER_NAME) in environment variables")
        return None, None, None
    return account_name, access_key, container

def _get_blob_service_client(account_name, access_key):
    """Creates a BlobServiceClient."""
    connection_string = (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={account_name};"
        f"AccountKey={access_key};"
        f"EndpointSuffix=core.windows.net"
    )
    return BlobServiceClient.from_connection_string(connection_string)

# --- Health Check --- 
def check_azure_connection(container_name: Optional[str] = None) -> bool:
    """Checks if a connection can be established with Azure Blob Storage."""
    logger.info("Checking Azure Blob Storage connection...")
    try:
        account_name, access_key, container_default = _get_azure_credentials()
        container = container_name or container_default
        if not account_name: # Credentials missing
            return False 
        
        blob_service_client = _get_blob_service_client(account_name, access_key)
        # Try listing containers (requires account-level permissions)
        # or get container properties (requires container-level permissions)
        container_client = blob_service_client.get_container_client(container)
        container_client.get_container_properties() # Throws exception if container doesn't exist or access denied
        logger.info(f"- Azure connection: OK (Able to access container '{container}')")
        return True
    except Exception as e:
        logger.error(f"- Azure connection: FAILED ({e})")
        return False

# --- New Path Construction Helper ---
def construct_blob_path(base_filename: str, publish_date_pst: Optional[datetime]) -> str:
    """Constructs the full blob path including date prefix if available.

    Args:
        base_filename: The base name of the file (e.g., 'data_uuid.json').
        publish_date_pst: Optional datetime object for the publish date.

    Returns:
        The full blob path (e.g., '2024/04/10/data_uuid.json' or 'data_uuid.json').
    """
    # Ensure filename has .json suffix if missing (optional, depends on how base_filename is generated)
    # if not base_filename.endswith('.json'):
    #     base_filename = f"{base_filename}.json"
    
    if publish_date_pst:
        date_prefix = publish_date_pst.strftime('%Y/%m/%d')
        return f"{date_prefix}/{base_filename}" 
    else:
        logger.warning(f"No publish_date_pst provided for blob '{base_filename}'. Returning path in container root.")
        return base_filename

def upload_markdown_to_azure(
    markdown_content: str,
    blob_name: Optional[str] = None,
    container_name: Optional[str] = None
) -> tuple[bool, str]:
    try:
        # Get Azure storage credentials from environment variables
        account_name = os.environ.get('AZ_ACCOUNT_NAME')
        access_key = os.environ.get('AZ_BLOB_ACCESS_KEY')
        container = container_name or os.environ.get('AZ_CONTAINER_NAME')
        
        # Validate required credentials
        if not account_name or not access_key or not container:
            logger.error("Missing Azure Storage credentials in environment variables")
            return False, "Azure Storage credentials not configured"
        
        # Generate a unique blob name if not provided
        if not blob_name:
            from uuid import uuid4
            blob_name = f"document_{uuid4()}.md"
        elif not blob_name.endswith('.md'):
            blob_name = f"{blob_name}.md"
        
        # Create connection string
        connection_string = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={account_name};"
            f"AccountKey={access_key};"
            f"EndpointSuffix=core.windows.net"
        )
        
        # Create blob service client
        blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(connection_string)
        
        # Get container client
        container_client = blob_service_client.get_container_client(container)
        
        # Create if container doesn't exist
        if not container_client.exists():
            container_client.create_container()
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Convert string to bytes
        blob_data = markdown_content.encode('utf-8')
        
        # Set content settings for markdown
        content_settings = ContentSettings(content_type='text/markdown')
        
        # Upload blob
        blob_client.upload_blob(
            blob_data,
            overwrite=True,
            content_settings=content_settings
        )
        
        # Construct and return the blob URL
        blob_url = f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}"
        logger.debug(f"Uploaded markdown to {blob_url}")
        
        return True, blob_url
        
    except Exception as e:
        logger.error(f"Error uploading to Azure Blob Storage: {str(e)}")
        return False, f"Error uploading to Azure Blob Storage: {str(e)}"

def upload_json_to_azure(
    json_data: dict,
    blob_name: Optional[str] = None,
    container_name: Optional[str] = None,
    pretty_print: bool = False,
    publish_date_pst: Optional[datetime] = None
) -> tuple[bool, str]:
    try:
        import json
        
        # Get Azure storage credentials using helper
        account_name, access_key, container_default = _get_azure_credentials()
        container = container_name or container_default
        
        # Validate required credentials
        if not account_name:
            # Error already logged by _get_azure_credentials
            return False, "Azure Storage credentials not configured"
        
        # Generate a unique blob name if not provided
        base_blob_name = blob_name
        if not base_blob_name:
            from uuid import uuid4
            base_blob_name = f"data_{uuid4()}.json"
        elif not base_blob_name.endswith('.json'):
            base_blob_name = f"{base_blob_name}.json"

        # Prepend date folder structure if publish_date_pst is provided
        final_blob_name = construct_blob_path(base_blob_name, publish_date_pst)
        
        # Create blob service client using helper
        blob_service_client = _get_blob_service_client(account_name, access_key)
        
        # Get container client
        container_client = blob_service_client.get_container_client(container)
        
        # Create if container doesn't exist
        if not container_client.exists():
            container_client.create_container()
            # Set container to public access for direct URL access
        
        # Get blob client using the final name (potentially with date prefix)
        blob_client = container_client.get_blob_client(final_blob_name)
        
        # Convert JSON to string and then to bytes
        if pretty_print:
            json_string = json.dumps(json_data, indent=4, sort_keys=True)
        else:
            json_string = json.dumps(json_data)
        
        blob_data = json_string.encode('utf-8')
        
        # Set content settings for JSON
        content_settings = ContentSettings(content_type='application/json')
        
        # Upload blob
        blob_client.upload_blob(
            blob_data,
            overwrite=True,
            content_settings=content_settings
        )
        
        # Construct and return the blob URL
        blob_url = f"https://{account_name}.blob.core.windows.net/{container}/{final_blob_name}"
        logger.debug(f"Uploaded JSON to {blob_url}")
        
        return True, blob_url
        
    except Exception as e:
        logger.error(f"Error uploading to Azure Blob Storage: {str(e)}")
        return False, f"Error uploading to Azure Blob Storage: {str(e)}"

def list_blobs_by_date_prefix(
    date_prefix: str, # Expects format like "YYYY/MM/DD" or "YYYY/MM"
    container_name: Optional[str] = None
) -> list[str]:
    """Lists blob names in Azure container that match the given date prefix.

    Args:
        date_prefix: The date prefix (e.g., "2025/04/10" or "2025/04").
        container_name: Optional name of the container. Defaults to env variable.

    Returns:
        A list of blob names matching the prefix.
    """
    blob_names = []
    try:
        account_name, access_key, container_default = _get_azure_credentials()
        container = container_name or container_default

        if not account_name:
            # Error already logged
            return []

        blob_service_client = _get_blob_service_client(account_name, access_key)
        container_client = blob_service_client.get_container_client(container)

        if not container_client.exists():
            logger.warning(f"Container '{container}' does not exist. Cannot list blobs.")
            return []

        logger.info(f"Listing blobs in container '{container}' with prefix '{date_prefix}'...")
        blob_list = container_client.list_blobs(name_starts_with=date_prefix)
        
        count = 0
        for blob in blob_list:
            blob_names.append(blob.name)
            count += 1
        
        logger.info(f"Found {count} blobs matching prefix '{date_prefix}'.")
        return blob_names

    except Exception as e:
        logger.error(f"Error listing blobs with prefix '{date_prefix}': {e}")
        return [] # Return empty list on error

# --- New Download Function --- 
async def download_json_from_azure(blob_path: str) -> Optional[Dict[str, Any]]:
    """Downloads and parses a JSON blob from Azure Storage.

    Args:
        blob_path: The full path to the blob within the container (e.g., '2024/04/10/file.json').

    Returns:
        The parsed dictionary, or None if download or parsing fails.
    """
    client = await get_blob_service_client()
    if not client:
        logger.error(f"Cannot download {blob_path}, failed to get Azure client.")
        return None

    blob_client = client.get_blob_client(container=container, blob=blob_path)

    try:
        logger.debug(f"Attempting to download blob: {blob_path}...")
        download_stream = await blob_client.download_blob()
        data = await download_stream.readall()
        logger.debug(f"Successfully downloaded blob: {blob_path}")
        
        # Decode and parse JSON
        json_data = json.loads(data.decode('utf-8'))
        return json_data
    except ResourceNotFoundError:
        logger.error(f"Blob not found: {blob_path}")
        return None
    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to parse JSON from blob {blob_path}: {json_err}")
        return None
    except Exception as e:
        logger.error(f"Failed to download or parse blob {blob_path}: {e}", exc_info=True)
        return None
    finally:
        # Avoid closing the shared client
        pass

# Consider adding a function to close the shared client explicitly on application shutdown
async def close_azure_connection():
    """Closes the shared Azure BlobServiceClient connection."""
    global _blob_service_client
    if _blob_service_client:
        try:
            await _blob_service_client.close()
            logger.info("Closed shared Azure BlobServiceClient.")
        except Exception as e:
            logger.error(f"Error closing Azure BlobServiceClient: {e}")
        finally:
             _blob_service_client = None