"""
Rate limiter utility for controlling request frequency during web scraping.
"""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """Simple rate limiter to control request frequency."""
    
    def __init__(self, delay_seconds: float = 1.0):
        """Initialize rate limiter.
        
        Args:
            delay_seconds: Minimum delay between requests
        """
        self.delay_seconds = delay_seconds
        self.last_request_time: Optional[float] = None
    
    async def wait(self):
        """Wait appropriate amount of time before next request."""
        current_time = time.time()
        
        if self.last_request_time is not None:
            elapsed = current_time - self.last_request_time
            if elapsed < self.delay_seconds:
                wait_time = self.delay_seconds - elapsed
                await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
