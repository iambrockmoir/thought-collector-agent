import logging
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, openai_client: OpenAI, storage_service=None, vector_service=None):
        self.client = openai_client
        self.storage = storage_service
        self.vector = vector_service

    def process_message(self, message: str, phone_number: str) -> str:
        """Process a chat message and return response"""
        try:
            # Create messages for ChatGPT
            messages = [
                {"role": "system", "content": "You are a helpful assistant who helps people organize and reflect on their thoughts."},
                {"role": "user", "content": message}
            ]
            
            # Get response from ChatGPT
            logger.info("Sending to ChatGPT...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            logger.info(f"ChatGPT response: {ai_response[:50]}...")  # Log first 50 chars
            
            # Store messages if storage service is available
            if self.storage:
                self.storage.store_chat_message(phone_number, message, True)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            return "Sorry, I encountered an error. Please try again."
