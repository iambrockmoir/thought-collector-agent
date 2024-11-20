import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase_client, vector_service=None):
        self.db = supabase_client
        self.vector = vector_service
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

    def store_thought(self, phone_number: str, audio_url: str, transcription: str) -> Optional[str]:
        """Store a thought from audio"""
        try:
            thought_data = {
                'user_phone': phone_number,
                'audio_url': audio_url,
                'transcription': transcription,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.db.table('thoughts').insert(thought_data).execute()
            thought_id = result.data[0]['id']
            logger.info(f"Stored thought with ID: {thought_id}")

            # Store in vector database if available
            if self.vector and transcription:
                try:
                    logger.info(f"Getting embedding for thought: {transcription[:50]}...")
                    embedding_response = openai_client.embeddings.create(
                        model="text-embedding-3-small",
                        input=transcription
                    )
                    embedding = embedding_response.data[0].embedding
                    logger.info("Successfully got embedding")
                    
                    metadata = {
                        'thought_id': thought_id,
                        'user_phone': phone_number,
                        'created_at': thought_data['created_at']
                    }
                    
                    vector_id = self.vector.store_vector(
                        text=transcription,
                        embedding=embedding,
                        metadata=metadata
                    )
                    logger.info(f"Successfully stored vector with ID: {vector_id}")
                except Exception as e:
                    logger.error(f"Failed to store vector: {str(e)}", exc_info=True)
            else:
                logger.info("Skipping vector storage: %s", 
                           "No vector service" if not self.vector else "No transcription")
            
            return thought_id
            
        except Exception as e:
            logger.error(f"Failed to store thought: {str(e)}", exc_info=True)
            return None 