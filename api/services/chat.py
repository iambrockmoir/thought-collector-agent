import logging
from datetime import datetime
from openai import OpenAI
from typing import List, Dict

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, openai_client: OpenAI, storage_service=None, vector_service=None):
        self.client = openai_client
        self.storage = storage_service
        self.vector = vector_service

    def process_message(self, message: str, phone_number: str) -> str:
        """Process a chat message and return response"""
        try:
            # Get relevant thoughts using vector similarity
            relevant_thoughts = self.storage.search_thoughts(
                user_phone=phone_number,
                query=message,
                limit=3
            )
            
            # Format thoughts as context
            thought_context = self._format_thought_context(relevant_thoughts)
            
            # Create messages for ChatGPT with context
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant who helps people reflect on their thoughts. "
                        "Below are some relevant thoughts the user previously recorded: \n\n"
                        f"{thought_context}\n\n"
                        "Use this context to provide more relevant responses to the user's query."
                    )
                },
                {"role": "user", "content": message}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=150
            )
            
            ai_response = response.choices[0].message.content
            
            # Store the interaction synchronously
            if self.storage:
                self.storage.store_chat_message(
                    phone_number, 
                    message, 
                    ai_response,
                    [t['id'] for t in relevant_thoughts]
                )
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            return "Sorry, I encountered an error. Please try again."

    def _format_thought_context(self, thoughts: List[Dict]) -> str:
        """Format thoughts into a string for context"""
        if not thoughts:
            return "No relevant thoughts found."
        
        context = []
        for thought in thoughts:
            context.append(f"- {thought['transcription']}")
        
        return "\n".join(context)
