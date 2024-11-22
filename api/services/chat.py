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

    async def process_message(self, user_phone: str, message: str) -> str:
        """Process a chat message and return a response"""
        try:
            # Await the search_thoughts call
            relevant_thoughts = await self.storage.search_thoughts(
                query=message,
                limit=5
            )
            
            # Get thought IDs for storage (if any)
            thought_ids = [t.id for t in relevant_thoughts if hasattr(t, 'id')] if relevant_thoughts else []
            
            # Format thoughts for context
            thought_context = self._format_thought_context(relevant_thoughts)

            # Generate response using ChatGPT
            messages = [
                {"role": "system", "content": "You are a helpful assistant managing a user's thoughts and memories."},
                {"role": "user", "content": f"Context: {thought_context}\n\nUser question: {message}"}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=150
            )
            
            reply = response.choices[0].message.content

            # Store the chat interaction
            await self.storage.store_chat_message(
                message=message,
                from_number=user_phone,
                response=reply,
                related_thought_ids=thought_ids if thought_ids else None
            )
            
            return reply

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "I apologize, but I encountered an error processing your message. Please try again."

    def _format_thought_context(self, thoughts: List[Dict]) -> str:
        """Format thoughts into a string for context"""
        if not thoughts:
            return "No relevant thoughts found."
        
        context = []
        for thought in thoughts:
            context.append(f"- {thought['transcription']}")
        
        return "\n".join(context)
