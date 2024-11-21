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
        self.vector = vector_service
        self.messages_table = 'chat_history'
        self.thoughts_table = 'thoughts'
        logger.info(f"Storage service initialized with vector service: {bool(vector_service)}")

    async def store_chat_message(self, message: str, from_number: str = None, response: str = None, related_thought_ids: List[str] = None) -> None:
        """Store a chat message in the database"""
        try:
            # Validate required fields
            if not message:
                logger.error("Cannot store message: message text is required")
                return
            
            if not from_number:
                logger.error("Cannot store message: phone number is required")
                return
            
            # Store user message
            user_data = {
                'user_phone': from_number,
                'message': message,
                'is_user': True,
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"Storing user message: {user_data}")
            result = self.supabase.table(self.messages_table).insert(user_data).execute()
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Supabase error: {result.error}")
            
            # If there's a response, store it as a separate message
            if response:
                response_data = {
                    'user_phone': from_number,
                    'message': response,
                    'is_user': False,
                    'created_at': datetime.now().isoformat()
                }
                logger.info(f"Storing assistant response: {response_data}")
                result = self.supabase.table(self.messages_table).insert(response_data).execute()
                if hasattr(result, 'error') and result.error:
                    raise Exception(f"Supabase error storing response: {result.error}")
                
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
                return []  # Return empty list instead of failing

            # Get vector search results
            results = self.vector.search(query, limit)
            
            # If user_phone is provided, filter results for that user
            if user_phone and results:
                filtered_results = [
                    r for r in results 
                    if r.metadata and r.metadata.get('user_phone') == user_phone
                ]
                return filtered_results
            
            return results or []  # Ensure we always return a list

        except Exception as e:
            logger.error(f"Thought search error: {str(e)}")
            return []  # Return empty list on error