"""
Token usage tracker for OpenAI API calls.

Tracks and limits token usage for OpenAI API calls.
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger

class TokenUsageTracker:
    """Tracks token usage for OpenAI API calls."""
    
    def __init__(self, storage_path: str = None):
        """Initialize the token usage tracker."""
        # Ensure the metrics directory exists
        metrics_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'data', 'metrics')
        os.makedirs(metrics_dir, exist_ok=True)
        
        self.storage_path = storage_path or os.path.join(metrics_dir, 'llm_token_usage.json')
        self.daily_limit = int(os.getenv("LLM_DAILY_TOKEN_LIMIT", "1000000"))
        self.monthly_limit = int(os.getenv("LLM_MONTHLY_TOKEN_LIMIT", "30000000"))
        self.alert_percent = int(os.getenv("LLM_ALERT_AT_PERCENT", "80"))
        self.track_usage = os.getenv("LLM_TRACK_USAGE", "true").lower() == "true"
        
        # Initialize or load usage data
        self._load_usage_data()
        
    def _load_usage_data(self) -> None:
        """Load token usage data from storage."""
        if not self.track_usage:
            self.usage_data = self._get_empty_usage_data()
            return
            
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self.usage_data = json.load(f)
                    
                # Check if we need to reset daily or monthly counters
                today = datetime.now().strftime('%Y-%m-%d')
                current_month = datetime.now().strftime('%Y-%m')
                
                if self.usage_data.get('daily_date') != today:
                    logger.info(f"Resetting daily token counter (was: {self.usage_data.get('daily_tokens', 0)})")
                    self.usage_data['daily_tokens'] = 0
                    self.usage_data['daily_date'] = today
                    
                if self.usage_data.get('monthly_date') != current_month:
                    logger.info(f"Resetting monthly token counter (was: {self.usage_data.get('monthly_tokens', 0)})")
                    self.usage_data['monthly_tokens'] = 0
                    self.usage_data['monthly_date'] = current_month
            else:
                self.usage_data = self._get_empty_usage_data()
        except Exception as e:
            logger.error(f"Error loading token usage data: {str(e)}")
            self.usage_data = self._get_empty_usage_data()
            
    def _get_empty_usage_data(self) -> Dict[str, Any]:
        """Get empty usage data structure."""
        return {            'daily_tokens': 0,
            'monthly_tokens': 0,
            'total_tokens': 0,
            'daily_date': datetime.now().strftime('%Y-%m-%d'),
            'monthly_date': datetime.now().strftime('%Y-%m'),
            'request_count': 0,
            'last_updated': datetime.now().isoformat(),
            'models': {}
        }
        
    def _save_usage_data(self) -> None:
        """Save token usage data to storage."""
        if not self.track_usage:
            return
            
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving token usage data: {str(e)}")
            
    def record_usage(self, model: str, tokens: int, request_type: str = 'completion') -> None:
        """Record token usage for an API call."""
        if not self.track_usage:
            return
            
        try:
            # Update usage counters
            self.usage_data['daily_tokens'] += tokens
            self.usage_data['monthly_tokens'] += tokens
            self.usage_data['total_tokens'] += tokens
            self.usage_data['request_count'] += 1
            self.usage_data['last_updated'] = datetime.now().isoformat()
            
            # Update model-specific counters
            if model not in self.usage_data['models']:
                self.usage_data['models'][model] = {
                    'tokens': 0, 'requests': 0, 'types': {}
                }                
            self.usage_data['models'][model]['tokens'] += tokens
            self.usage_data['models'][model]['requests'] += 1
            
            # Update request type counters
            if request_type not in self.usage_data['models'][model]['types']:
                self.usage_data['models'][model]['types'][request_type] = {
                    'tokens': 0, 'requests': 0
                }
                
            self.usage_data['models'][model]['types'][request_type]['tokens'] += tokens
            self.usage_data['models'][model]['types'][request_type]['requests'] += 1
            
            # Save updated usage data
            self._save_usage_data()
            
            # Check if we're approaching limits
            self._check_limits()
        except Exception as e:
            logger.error(f"Error recording token usage: {str(e)}")
    
    def can_make_request(self, estimated_tokens: int = 1000) -> bool:
        """Check if a request can be made without exceeding limits."""
        if not self.track_usage:
            return True
            
        daily_usage = self.usage_data['daily_tokens'] + estimated_tokens
        monthly_usage = self.usage_data['monthly_tokens'] + estimated_tokens
        
        return daily_usage <= self.daily_limit and monthly_usage <= self.monthly_limit
        
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current token usage statistics."""
        if not self.track_usage:
            return {'tracking_enabled': False, 'message': 'Token usage tracking is disabled'}
            
        daily_percent = (self.usage_data['daily_tokens'] / self.daily_limit) * 100
        monthly_percent = (self.usage_data['monthly_tokens'] / self.monthly_limit) * 100
        
        return {
            'tracking_enabled': True,
            'daily_usage': {
                'tokens': self.usage_data['daily_tokens'],
                'limit': self.daily_limit,
                'percent': daily_percent,
                'remaining': self.daily_limit - self.usage_data['daily_tokens'],
                'date': self.usage_data['daily_date']
            },
            'monthly_usage': {
                'tokens': self.usage_data['monthly_tokens'],
                'limit': self.monthly_limit,
                'percent': monthly_percent,
                'remaining': self.monthly_limit - self.usage_data['monthly_tokens'],
                'date': self.usage_data['monthly_date']
            },
            'total_usage': {
                'tokens': self.usage_data['total_tokens'],
                'requests': self.usage_data['request_count']
            },
            'models': self.usage_data['models'],
            'last_updated': self.usage_data['last_updated']
        }
        
    def _check_limits(self) -> None:
        """Check if token usage is approaching limits."""
        try:
            daily_percent = (self.usage_data['daily_tokens'] / self.daily_limit) * 100
            monthly_percent = (self.usage_data['monthly_tokens'] / self.monthly_limit) * 100
            
            if daily_percent >= self.alert_percent:
                logger.warning(f"Daily token usage at {daily_percent:.2f}% of limit")
            if monthly_percent >= self.alert_percent:
                logger.warning(f"Monthly token usage at {monthly_percent:.2f}% of limit")
        except Exception as e:
            logger.error(f"Error checking token limits: {str(e)}")