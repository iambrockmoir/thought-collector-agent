import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase_client, vector_service=None):
        self.supabase = supabase_client
        self.vector = vector_service
        logger.info(f"Storage service initialized with vector service: {vector_service is not None}")

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using vector service"""
        if not self.vector:
            logger.error("Vector service not initialized")
            return []
        return self.vector.generate_embedding(text)

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