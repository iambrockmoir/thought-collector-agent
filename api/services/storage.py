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
        logger.info(f"Storage service initialized with vector service: {vector_service is not None}")

    async def store_chat_message(self, user_phone: str, message: str, response: str, related_thought_ids: List[str] = None) -> bool:
        """Store a chat interaction in Supabase"""
        try:
            chat_data = {
                "user_phone": user_phone,
                "message": message,
                "response": response,
                "related_thought_ids": related_thought_ids or [],
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table('chat_history').insert(chat_data).execute()
            
            if hasattr(response, 'error') and response.error is not None:
                logger.error(f"Failed to store chat message in Supabase: {response.error}")
                return False
                
            return True

        except Exception as e:
            logger.error(f"Failed to store chat message: {str(e)}")
            return False

    def store_thought(self, user_phone: str, transcription: str) -> bool:
        """Store a thought in both Supabase and vector store"""
        try:
            # Prepare metadata
            full_metadata = {
                "user_phone": user_phone,
                "transcription": transcription,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store in Supabase
            thought_data = {
                "user_phone": user_phone,
                "transcription": transcription,
                "created_at": full_metadata["created_at"]
            }
            
            response = self.supabase.table('thoughts').insert(thought_data).execute()
            
            if hasattr(response, 'error') and response.error is not None:
                logger.error(f"Failed to store thought in Supabase: {response.error}")
                return False

            # Store embedding in Pinecone
            if self.vector:
                return self.vector.store_embedding(transcription, full_metadata)
            
            return True

        except Exception as e:
            logger.error(f"Failed to store thought: {str(e)}")
            return False

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