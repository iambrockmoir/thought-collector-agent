import logging
from datetime import datetime
from openai import OpenAI
from typing import List, Dict

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, openai_client: OpenAI, storage_service, vector_service):
        self.client = openai_client
        self.storage = storage_service
        self.vector = vector_service
        self.max_context_thoughts = 3  # Number of relevant thoughts to include

    async def process_message(self, message: str, phone_number: str) -> str:
        """Process a chat message and return response with relevant thought context"""
        try:
            # Get relevant thoughts using vector similarity
            relevant_thoughts = await self.storage.search_thoughts(
                user_phone=phone_number,
                query=message,
                limit=self.max_context_thoughts
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
            
            # Get response from ChatGPT
            logger.info("Sending to ChatGPT with thought context...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=150
            )
            
            ai_response = response.choices[0].message.content
            
            # Store the interaction
            if self.storage:
                await self.storage.store_chat_message(
                    phone_number, 
                    message, 
                    ai_response,
                    [t['id'] for t in relevant_thoughts]
                )
            
            # Ensure response isn't too long for SMS
            if len(ai_response) > 1500:
                ai_response = ai_response[:1497] + "..."
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            return "Sorry, I encountered an error. Please try again."

    def _format_thought_context(self, thoughts: List[Dict]) -> str:
        """Format thoughts into a context string"""
        if not thoughts:
            return "No relevant previous thoughts found."
            
        context_parts = []
        for thought in thoughts:
            timestamp = thought.get('created_at', '').split('T')[0]  # Get just the date
            context_parts.append(f"On {timestamp}, you said: {thought['transcription']}")
            
        return "\n\n".join(context_parts)
