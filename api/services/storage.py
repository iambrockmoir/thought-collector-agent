import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from supabase import create_client
from api.services.vector import VectorService

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase_client, vector_service=None):
        self.supabase = supabase_client
        self.vector_service = vector_service
        self.messages_table = 'messages'
        self.thoughts_table = 'thoughts'
        logger.info(f"Storage service initialized with vector service: {bool(vector_service)}")

    async def store_chat_message(self, from_number: str, message: str, is_user: bool = True) -> None:
        try:
            data = {
                'phone_number': from_number,
                'message': message,
                'is_user': is_user,
                'created_at': datetime.now().isoformat()
            }
            self.supabase.table(self.messages_table).insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to store chat message: {str(e)}")
            raise

    def store_thought(self, from_number: str, thought: str, embedding: Optional[List[float]] = None) -> None:
        try:
            data = {
                'phone_number': from_number,
                'thought': thought,
                'created_at': datetime.now().isoformat()
            }
            if embedding:
                data['embedding'] = embedding
            self.supabase.table(self.thoughts_table).insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to store thought: {str(e)}")
            raise

    def search_thoughts(self, query: str, user_phone: str = None, limit: int = 5) -> List[dict]:
        """Search for similar thoughts using vector similarity"""
        try:
            if not self.vector:
                logger.warning("Vector service not available for search")
                return []

            # Get vector search results
            results = self.vector.search(query, limit)
            
            # If user_phone is provided, filter results for that user
            if user_phone:
                filtered_results = [
                    r for r in results 
                    if r.metadata.get('user_phone') == user_phone
                ]
                return filtered_results
            
            return results

        except Exception as e:
            logger.error(f"Thought search error: {str(e)}")
            return []