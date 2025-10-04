"""
LLM-based content cleaning module for NewsRagnarok Crawler.

This module replaces regex-based cleaning with LLM to extract and clean article content.
"""
import os
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from openai import AzureOpenAI
from dotenv import load_dotenv

# Import environment validators and token tracker
from utils.config.env_validator import EnvironmentValidator
from utils.config.token_tracker import TokenUsageTracker

# Load environment variables
load_dotenv()

class LLMContentCleaner:
    """Content cleaner using LLM to extract and clean article content."""
    
    def __init__(self):
        """Initialize the LLM content cleaner."""
        # Validate environment and get configuration
        self.config_valid = EnvironmentValidator.validate_llm_config()
        self.llm_config = EnvironmentValidator.get_llm_config()
        
        # Initialize token tracker
        self.token_tracker = TokenUsageTracker()
        
        # Check if LLM cleaning is enabled
        self.enabled = EnvironmentValidator.is_llm_cleaning_enabled()
        if not self.enabled:
            logger.warning("LLM content cleaning is disabled due to configuration or missing environment variables.")
            self.client = None
            return
            
        # Initialize Azure OpenAI client
        try:
            self.client = AzureOpenAI(
                api_version=self.llm_config["api_version"],                azure_endpoint=self.llm_config["base_url"],
                api_key=self.llm_config["api_key"]
            )
            logger.info(f"LLM content cleaner initialized with model: {self.llm_config['completion_deployment']}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            self.client = None
            self.enabled = False    
    async def clean_content(self, raw_content: str, source_name: str, url: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Clean article content using LLM.
        
        Args:
            raw_content: The raw markdown content to clean.
            source_name: The name of the source (e.g., 'babypips').
            url: The URL of the article.
            
        Returns:
            Tuple of (cleaned_content, metadata) or None if cleaning failed.
        """
        # Check if LLM cleaning is enabled and client is initialized
        if not self.enabled or not self.client:
            logger.error("LLM client not initialized or disabled. Cannot clean content.")
            return None
        
        # Check if content is too short
        if not raw_content or len(raw_content.strip()) < 50:
            logger.warning(f"Content too short for LLM cleaning: {len(raw_content if raw_content else '')} chars")
            return None
            
        # Check if content is too long
        max_length = self.llm_config.get("max_content_length", 100000)
        if len(raw_content) > max_length:
            logger.warning(f"Content too long for LLM cleaning ({len(raw_content)} chars). Truncating to {max_length} chars.")
            raw_content = raw_content[:max_length]        
        # Check if we're within token limits
        estimated_tokens = len(raw_content.split()) * 1.5  # Rough estimate: words × 1.5
        if not self.token_tracker.can_make_request(int(estimated_tokens)):
            logger.error("Token limit exceeded. Cannot clean content.")
            
            # Try to send alert if we have the alerts module
            try:
                from monitoring.alerts import get_alert_manager
                alert_manager = get_alert_manager()
                alert_manager.send_alert(
                    "llm_token_limit_exceeded",
                    f"Token limit exceeded. Cannot clean content for {source_name}.",
                    "error"
                )
            except Exception:
                pass  # Continue even if alert fails
                
            return None
        
        try:
            # Create system prompt for content cleaning
            system_prompt = f"""
            You are an expert financial content processor for the NewsRagnarok Crawler system.
            Your task is to clean and extract financial news content from raw markdown, removing navigation elements, 
            ads, footers, and any content not directly related to the article itself.
            
            The content comes from {source_name} with URL: {url}
            
            Extract the following metadata:
            1. Title
            2. Author/creator (if available)
            3. Date/time (if available)
            4. Category/tags (if available)            
            Then provide the cleaned article text maintaining:
            - All financial data and values
            - All market analysis
            - Important quotes and statements
            - Chart descriptions and technical analysis
            - Trading advice and market sentiment
            - Price levels, support/resistance, and technical indicators
            
            Remove:
            - Navigation menus and site headers/footers
            - Advertisements and promotional content
            - Sidebars and widgets
            - User comments sections
            - Social media buttons and sharing links
            - Duplicate content, especially repeated titles
            - Any content not directly related to the financial article
            
            Format your response as clean markdown with the following structure:
            
            ```json
            {{
                "title": "Extracted article title",
                "author": "Author name if found, or empty string",
                "date": "Date if found, or empty string",
                "category": "Category if found, or empty string",
                "cleaned_content": "Full cleaned article text in markdown format"
            }}
            ```
            
            Be sure to maintain all financial information and analysis intact. Your task is content cleaning,
            not summarization.
            """            
            # Create user prompt with raw content
            user_prompt = f"Here is the raw content to process:\n\n{raw_content}"
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.llm_config["completion_deployment"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.llm_config.get("token_limit", 4000),
                temperature=self.llm_config.get("temperature", 0.1)
            )
            
            # Record token usage
            completion_tokens = response.usage.completion_tokens
            prompt_tokens = response.usage.prompt_tokens
            total_tokens = response.usage.total_tokens
            
            self.token_tracker.record_usage(
                model=self.llm_config["completion_deployment"],
                tokens=total_tokens,
                request_type="content_cleaning"
            )
            
            logger.info(f"LLM usage: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total tokens")
            
            # Extract JSON from response
            import json
            import re            
            # Find JSON in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response.choices[0].message.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                cleaned_data = json.loads(json_str)
            else:
                # Try direct JSON parsing if not in code block
                cleaned_data = json.loads(response.choices[0].message.content)
            
            # Extract data from response
            title = cleaned_data.get('title', '')
            author = cleaned_data.get('author', '')
            date = cleaned_data.get('date', '')
            category = cleaned_data.get('category', '')
            cleaned_content = cleaned_data.get('cleaned_content', '')
            
            # Create metadata dictionary
            metadata = {
                "title": title,
                "author": author,
                "date": date,
                "category": category
            }
            
            # Format cleaned content with metadata
            final_content = f"# {title}\n\n"
            if author:
                final_content += f"Author: {author}\n\n"
            if date:
                final_content += f"Date: {date}\n\n"
            if category:
                final_content += f"Category: {category}\n\n"
            
            final_content += cleaned_content            
            logger.info(f"Successfully cleaned content with LLM. Original: {len(raw_content)} chars, Cleaned: {len(final_content)} chars")
            
            # Try to track metrics if available
            try:
                from monitoring.metrics import get_metrics
                metrics = get_metrics()
                metrics.record_llm_cleaning_success(source_name)
            except Exception:
                pass  # Continue even if metrics fail
                
            return final_content, metadata
            
        except Exception as e:
            logger.error(f"Error cleaning content with LLM: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Try to track metrics if available
            try:
                from monitoring.metrics import get_metrics
                metrics = get_metrics()
                metrics.record_llm_cleaning_failure(source_name, str(e))
            except Exception:
                pass  # Continue even if metrics fail
                
            return None        
    
    async def is_healthy(self) -> bool:
        """Check if the LLM cleaner is healthy and ready to use."""
        if not self.enabled or not self.client:
            return False
            
        try:            # Check if we're within token limits
            if not self.token_tracker.can_make_request(20):  # Small request just to check
                logger.error("Token limit exceeded. Health check failed.")
                return False
                
            # Try a simple completion to test the connection
            response = self.client.chat.completions.create(
                model=self.llm_config["completion_deployment"],
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            # Record token usage
            if response and hasattr(response, 'usage'):
                self.token_tracker.record_usage(
                    model=self.llm_config["completion_deployment"],
                    tokens=response.usage.total_tokens,
                    request_type="health_check"
                )
            
            return response is not None and len(response.choices) > 0
        except Exception as e:
            logger.error(f"LLM health check failed: {str(e)}")
            return False
    
    def get_token_usage(self) -> Dict[str, Any]:
        """Get token usage statistics.
        
        Returns:
            Dictionary with token usage statistics
        """
        return self.token_tracker.get_usage_stats()


# Factory function for easy cleaner creation
def create_llm_cleaner() -> LLMContentCleaner:
    """Factory function to create an LLM content cleaner.
    
    Returns:
        LLMContentCleaner instance
    """
    return LLMContentCleaner()