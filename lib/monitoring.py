import logging
from typing import Dict, Any

class Monitor:
    def log_chat_metrics(self, data: Dict[str, Any]) -> None:
        """Log chat performance metrics"""
        pass

    def log_vector_search_metrics(self, data: Dict[str, Any]) -> None:
        """Log vector search performance"""
        pass 