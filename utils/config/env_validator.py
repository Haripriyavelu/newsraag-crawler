"""
Environment validator for NewsRagnarok Crawler.

Validates required environment variables for system components.
"""
import os
from typing import List, Dict, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EnvironmentValidator:
    """Validates required environment variables for system components."""
    
    @staticmethod
    def validate_llm_config() -> Dict[str, bool]:
        """Validate LLM configuration environment variables.
        
        Returns:
            Dictionary with validation results for each component
        """
        results = {
            "azure_openai": False,
            "llm_cleaning": False,
            "vector_embedding": False
        }
        
        # Validate Azure OpenAI base configuration
        base_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "AZURE_OPENAI_API_VERSION"]
        base_valid = all(os.getenv(var) for var in base_vars)
        results["azure_openai"] = base_valid
        
        if not base_valid:
            missing = [var for var in base_vars if not os.getenv(var)]
            logger.error(f"Missing required Azure OpenAI configuration: {', '.join(missing)}")
        
        # Validate LLM cleaning configuration
        cleaning_vars = ["AZURE_OPENAI_DEPLOYMENT"]
        cleaning_valid = base_valid and all(os.getenv(var) for var in cleaning_vars)
        results["llm_cleaning"] = cleaning_valid
        
        if base_valid and not cleaning_valid:
            missing = [var for var in cleaning_vars if not os.getenv(var)]
            logger.error(f"Missing required LLM cleaning configuration: {', '.join(missing)}")
        
        # Validate vector embedding configuration
        embedding_vars = ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "AZURE_OPENAI_EMBEDDING_MODEL", "EMBEDDING_DIMENSION"]
        embedding_valid = base_valid and all(os.getenv(var) for var in embedding_vars)
        results["vector_embedding"] = embedding_valid
        
        if base_valid and not embedding_valid:
            missing = [var for var in embedding_vars if not os.getenv(var)]
            logger.error(f"Missing required vector embedding configuration: {', '.join(missing)}")
        
        return results
    
    @staticmethod
    def is_llm_cleaning_enabled() -> bool:
        """Check if LLM cleaning is enabled in configuration.
        
        Returns:
            True if LLM cleaning is enabled, False otherwise
        """
        # Check if explicitly disabled
        if os.getenv("LLM_CLEANING_ENABLED", "true").lower() == "false":
            return False
            
        # Check if configuration is valid
        validation = EnvironmentValidator.validate_llm_config()
        return validation["azure_openai"] and validation["llm_cleaning"]
        
    @staticmethod
    def get_llm_config() -> Dict[str, any]:
        """Get LLM configuration parameters.
        
        Returns:
            Dictionary with LLM configuration parameters
        """
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),            "completion_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            "embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            "embedding_model": os.getenv("AZURE_OPENAI_EMBEDDING_MODEL"),
            "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "3072")),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "token_limit": int(os.getenv("LLM_TOKEN_LIMIT_PER_REQUEST", "4000")),
            "max_content_length": int(os.getenv("LLM_MAX_CONTENT_LENGTH", "100000"))
        }