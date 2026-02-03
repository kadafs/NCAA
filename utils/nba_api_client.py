import time
import random
import requests
from nba_api.stats.endpoints._base import Endpoint

class RobustNBAClient:
    """
    Standardized wrapper for nba_api calls with retries and randomized headers.
    """
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
    ]

    @staticmethod
    def get_headers():
        return {
            'User-Agent': random.choice(RobustNBAClient.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

    @staticmethod
    def call_endpoint(endpoint_class, max_retries=3, **kwargs):
        """
        Calls an nba_api endpoint with retries and exponential backoff.
        """
        last_exception = None
        for i in range(max_retries):
            try:
                # Add randomized headers to kwargs
                kwargs['headers'] = RobustNBAClient.get_headers()
                
                # Create endpoint instance
                instance = endpoint_class(**kwargs)
                return instance.get_dict()
            
            except Exception as e:
                last_exception = e
                wait_time = (i + 1) * 5 + random.uniform(0, 2)
                print(f"NBA API Attempt {i+1} failed: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        raise last_exception
