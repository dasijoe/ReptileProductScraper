"""
Throttling utilities to prevent overloading websites with requests.
"""
import time
import logging
from datetime import datetime, timedelta

class Throttler:
    """
    Class to throttle requests to stay within rate limits.
    """
    def __init__(self, max_requests_per_minute=10):
        """
        Initialize the throttler.
        
        Args:
            max_requests_per_minute: Maximum number of requests allowed per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = []
        self.window_size = 60  # 60 seconds (1 minute)
    
    def throttle(self):
        """
        Throttle requests to stay within rate limits.
        If the rate limit would be exceeded, this method will sleep until it's safe to proceed.
        """
        now = datetime.now()
        
        # Remove request times outside the current window
        window_start = now - timedelta(seconds=self.window_size)
        self.request_times = [t for t in self.request_times if t >= window_start]
        
        # If we've reached the rate limit, wait until a request time expires
        if len(self.request_times) >= self.max_requests_per_minute:
            # Calculate how long to wait for the oldest request to expire from the window
            oldest_request = min(self.request_times)
            expire_time = oldest_request + timedelta(seconds=self.window_size)
            wait_seconds = (expire_time - now).total_seconds()
            
            if wait_seconds > 0:
                logging.info(f"Rate limit reached, throttling for {wait_seconds:.2f} seconds")
                time.sleep(wait_seconds)
        
        # Record the current request time
        self.request_times.append(datetime.now())
        
class AdaptiveThrottler(Throttler):
    """
    Advanced throttler that adapts to response status codes and response times.
    """
    def __init__(self, max_requests_per_minute=10, initial_delay=1.0):
        """
        Initialize the adaptive throttler.
        
        Args:
            max_requests_per_minute: Maximum number of requests allowed per minute
            initial_delay: Initial delay between requests in seconds
        """
        super().__init__(max_requests_per_minute)
        self.delay = initial_delay
        self.min_delay = 0.5
        self.max_delay = 10.0
        self.success_count = 0
        self.failure_count = 0
    
    def adjust_delay(self, success=True, status_code=None, response_time=None):
        """
        Adjust the delay based on the success or failure of the previous request.
        
        Args:
            success: Whether the previous request was successful
            status_code: HTTP status code of the previous request
            response_time: Response time of the previous request in seconds
        """
        if not success or (status_code and status_code >= 400):
            # Increase delay on failure
            self.failure_count += 1
            self.success_count = 0
            
            # Increase delay more aggressively for certain status codes
            if status_code in (403, 429):  # Forbidden or Too Many Requests
                self.delay = min(self.delay * 2.0, self.max_delay)
            else:
                self.delay = min(self.delay * 1.5, self.max_delay)
        else:
            # Decrease delay on consecutive successes
            self.success_count += 1
            self.failure_count = 0
            
            if self.success_count >= 10:
                self.delay = max(self.delay * 0.9, self.min_delay)
        
        # Adjust delay based on response time if available
        if response_time is not None and response_time > self.delay * 2:
            # If response time is much longer than our delay, increase delay
            self.delay = min(response_time * 0.5, self.max_delay)
            
        logging.debug(f"Adjusted throttling delay to {self.delay:.2f} seconds")
    
    def throttle(self):
        """
        Apply rate limiting and adaptive delay.
        """
        # First apply rate limiting from parent class
        super().throttle()
        
        # Then apply adaptive delay
        if self.delay > 0:
            time.sleep(self.delay)