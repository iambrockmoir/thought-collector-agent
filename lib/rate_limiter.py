from datetime import datetime
from typing import Dict

class RateLimiter:
    def __init__(self):
        self.limits = {}
        self.MAX_REQUESTS = 100  # per user per hour

    def check_limit(self, user_phone: str) -> bool:
        """Check if user has exceeded rate limit"""
        pass 