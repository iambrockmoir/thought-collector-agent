import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from supabase import create_client
from api.services.vector import VectorService

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, vector_service):
        self.vector = vector_service
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        logger.info(f"Storage service initialized with vector service: {vector_service is not None}")

    def store_thought(self, user_phone: str, audio_url: str, transcription: str, metadata: dict = None) -> bool:
        """Store a thought in Supabase and its embedding in Pinecone"""
        try:
            # Store metadata in Supabase
            thought_data = {
                'user_phone': user_phone,
                'audio_url': audio_url,
                'transcription': transcription,
                'metadata': metadata or {}
            }
            
            response = self.supabase.table('thoughts').insert(thought_data).execute()
            
            if hasattr(response, 'error') and response.error is not None:
                logger.error(f"Failed to store thought in Supabase: {response.error}")
                return False

            # Store embedding in Pinecone if vector service is available
            if self.vector and transcription:
                self.vector.store_embedding(transcription, metadata={'user_phone': user_phone})

            return True

        except Exception as e:
            logger.error(f"Failed to store thought: {str(e)}")
            return False

    def store_chat_message(self, phone_number: str, message: str, response: str, thought_ids: List[str] = None):
        """Store chat message in database"""
        try:
            data = {
                'user_phone': phone_number,
                'message': message,
                'response': response,
                'thought_ids': thought_ids or []
            }
            self.supabase.table('chat_history').insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to store chat message: {str(e)}")
            return False

    async def store_chat_message(
        self, 
        user_phone: str, 
        message: str, 
        response: str,
        related_thought_ids: List[str]
    ) -> str:
        """Store a chat message with references to related thoughts"""
        try:
            chat_record = {
                'user_phone': user_phone,
                'message': message,
                'response': response,
                'related_thoughts': related_thought_ids,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = await self.db.table('chat_history').insert(chat_record).execute()
            return result.data[0]['id']
            
        except Exception as e:
            logger.error(f"Failed to store chat message: {str(e)}")
            return None 

    def search_thoughts(
        self,
        user_phone: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for relevant thoughts using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)
            
            # Search Pinecone for similar thoughts
            similar_thoughts = self.pinecone.similarity_search(
                query_embedding,
                filter={'user_phone': user_phone},
                limit=limit
            )
            
            # Get full thought records from Supabase
            thought_ids = [thought['id'] for thought in similar_thoughts]
            thoughts = self.supabase.table('thoughts')\
                .select('*')\
                .in_('id', thought_ids)\
                .execute()

            return thoughts.data

        except Exception as e:
            logger.error(f"Thought search error: {str(e)}")
            return []