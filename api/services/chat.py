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

    def _build_system_prompt(self, context: str) -> str:
        """Build the system prompt with context"""
        base_prompt = (
            "You are a helpful assistant and life coach who helps users capture and interact with their thoughts."
            "You have access to past thoughts the user has given you that are relevant to the user's query."
            "You will be replying via SMS, so keep your responses concise and to the point."
            "When responding, if the user asks a question, you should respond with just the answer from the context you have."
            "When responding, if the user is recording a thought, you should follow up with an insight related to their thought and the context you have."
        )
        
        if context:
            return f"{base_prompt}\n\nRelevant context from user's previous thoughts:\n{context}"
        return base_prompt

    async def process_message(self, user_phone: str, message: str) -> str:
        """Process a chat message and return a response"""
        try:
            # Search for relevant context
            results = await self.storage.search_thoughts(message, limit=20)
            
            # Build context from search results
            context = []
            for result in results:
                # Access metadata safely
                metadata = result.metadata if hasattr(result, 'metadata') else {}
                text = metadata.get('text', '')  # Use get() with default value
                if text:
                    context.append(text)
            
            # If no context found, proceed with empty context
            context_str = "\n\n".join(context) if context else ""
            
            # Build the prompt
            system_prompt = self._build_system_prompt(context_str)
            
            # Get completion from OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=150
            )
            
            return response.choices[0].message.content

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
