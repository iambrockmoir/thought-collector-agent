import logging
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase_client, vector_service=None, openai_client=None):
        self.db = supabase_client
        self.vector = vector_service
        self.openai = openai_client
        logger.info("Storage service initialized with vector service: %s", 
                   "yes" if vector_service else "no")

    def store_chat_message(self, phone_number: str, content: str, is_user: bool) -> Optional[str]:
        """Store a chat message in the database"""
        try:
            data = {
                'user_phone': phone_number,
                'message': content,
                'is_user': is_user,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.db.table('chat_history').insert(data).execute()
            logger.info(f"Stored chat message for {phone_number}")
            return response.data[0]['id'] if response.data else None
            
        except Exception as e:
            logger.error(f"Failed to store chat message: {str(e)}")
            return None

    def store_thought(self, from_number: str, media_url: str = None, transcription: str = None) -> str:
        """Store a thought in the database and vector store"""
        try:
            # Store in Supabase with correct column names
            thought = {
                'user_phone': from_number,      # Changed from 'from_number'
                'audio_url': media_url,         # Changed from 'media_url'
                'transcription': transcription,
                'metadata': {}                  # Add empty metadata object
            }
            
            response = self.db.table('thoughts').insert(thought).execute()
            thought_id = response.data[0]['id']
            logger.info(f"Stored thought with ID: {thought_id}")
            
            # Store vector embedding if available
            if self.vector and transcription:
                logger.info(f"Getting embedding for thought: {transcription[:50]}...")
                embedding_response = self.openai.embeddings.create(
                    model="text-embedding-ada-002",
                    input=transcription
                )
                embedding = embedding_response.data[0].embedding
                
                self.vector.store_vector(
                    thought_id,
                    embedding,
                    {'text': transcription}
                )
                logger.info("Vector stored successfully")
            
            return thought_id
            
        except Exception as e:
            logger.error(f"Failed to store vector: {str(e)}", exc_info=True)
            return None 

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