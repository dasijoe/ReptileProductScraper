"""
Utility for throttling requests to avoid overwhelming target websites.
"""
import time
from collections import deque

class Throttler:
    """
    Class for implementing rate limiting to avoid overwhelming websites.
    """
    def __init__(self, max_requests_per_minute):
        """
        Initialize the throttler.
        
        Args:
            max_requests_per_minute: Maximum number of requests allowed per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = deque()
        self.window_size = 60  # 1 minute window
    
    def throttle(self):
        """
        Throttle requests to stay within rate limits.
        
        This will sleep if too many requests have been made recently.
        """
        current_time = time.time()
        
        # Remove old request times
        while self.request_times and current_time - self.request_times[0] > self.window_size:
            self.request_times.popleft()
        
        # Check if we're at the rate limit
        if len(self.request_times) >= self.max_requests_per_minute:
            # Calculate how long to wait
            oldest_request = self.request_times[0]
            wait_time = self.window_size - (current_time - oldest_request)
            
            if wait_time > 0:
                time.sleep(wait_time)
                current_time = time.time()
        
        # Add current request time
        self.request_times.append(current_time)
    
    def reset(self):
        """
        Reset the throttler's request times.
        """
        self.request_times.clear()
