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
        if vector_service is None:
            logger.warning("Vector service not provided to storage service")
        else:
            logger.info("Vector service successfully connected to storage service")
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
                'user_phone': from_number,
                'transcription': thought,
                'created_at': datetime.now().isoformat()
            }
            if embedding:
                data['metadata'] = {'embedding': embedding}
            
            logger.info(f"Storing thought in Supabase: {data}")
            result = self.supabase.table(self.thoughts_table).insert(data).execute()
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Supabase error: {result.error}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to store thought: {str(e)}")
            raise

    async def search_thoughts(self, query: str, limit: int = 5) -> List[Dict]:
        try:
            if not self.vector_service:
                logger.warning("Vector service not available for search")
                return []
            
            # Await the async search
            relevant_thoughts = await self.vector_service.search(query, limit)
            return relevant_thoughts
            
        except Exception as e:
            logger.error(f"Thought search error: {str(e)}")
            return []