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
            # Search for relevant thoughts
            relevant_thoughts = self.storage.search_thoughts(
                query=message,
                user_phone=user_phone,  # Pass user_phone to filter results
                limit=5
            )
            
            # Format thoughts for context
            thought_context = ""
            if relevant_thoughts:
                thought_context = "Here are some relevant thoughts I found:\n"
                for i, thought in enumerate(relevant_thoughts, 1):
                    thought_context += f"{i}. {thought.metadata.get('transcription', 'No transcription available')}\n"
            else:
                thought_context = "I couldn't find any relevant thoughts in your history."

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
            await self.storage.store_chat_message(user_phone, message, reply)
            
            return reply

        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            raise

    def _format_thought_context(self, thoughts: List[Dict]) -> str:
        """Format thoughts into a string for context"""
        if not thoughts:
            return "No relevant thoughts found."
        
        context = []
        for thought in thoughts:
            context.append(f"- {thought['transcription']}")
        
        return "\n".join(context)
