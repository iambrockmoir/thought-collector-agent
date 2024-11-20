import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase_client):
        self.db = supabase_client

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
            return thought_id
            
        except Exception as e:
            logger.error(f"Failed to store thought: {str(e)}")
            return None 