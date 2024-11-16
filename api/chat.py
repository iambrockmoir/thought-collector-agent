from typing import Dict, List, Optional, Any
from datetime import datetime
from lib.openai_client import OpenAIClient
from lib.error_handler import AppError

class ChatEngine:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.conversation_context = {}
        self.MAX_HISTORY = 10  # Make configurable
        self.CONTEXT_TIMEOUT = 1800  # 30 minutes, make configurable

    async def process_query(
        self,
        user_phone: str,
        message: str,
        max_context_thoughts: int = 5
    ) -> Dict[str, Any]:
        """
        Process an incoming chat message and generate a response
        """
        try:
            # Get conversation context for this user
            context = self.maintain_conversation_context(user_phone)
            
            # Create prompt with context
            prompt = self._create_chat_prompt(message, context)
            
            # Generate response using OpenAI
            response = await self.openai_client.generate_response(
                query=prompt,
                context=self._format_context(context)
            )

            # Update conversation history
            self.handle_conversation_history(
                user_phone=user_phone,
                message=message,
                response=response
            )

            return {
                "response": response,
                "context_used": bool(context.get('messages')),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            raise AppError(f"Chat processing error: {str(e)}", status_code=500)

    def maintain_conversation_context(self, user_phone: str) -> Dict:
        """
        Maintain conversation context for a user
        """
        if user_phone not in self.conversation_context:
            self.conversation_context[user_phone] = {
                'messages': [],
                'last_updated': datetime.utcnow()
            }
        
        # Clear context if it's been too long (e.g., 30 minutes)
        last_updated = self.conversation_context[user_phone]['last_updated']
        if (datetime.utcnow() - last_updated).seconds > self.CONTEXT_TIMEOUT:  # 30 minutes
            self.conversation_context[user_phone]['messages'] = []
        
        self.conversation_context[user_phone]['last_updated'] = datetime.utcnow()
        return self.conversation_context[user_phone]

    def handle_conversation_history(
        self,
        user_phone: str,
        message: str,
        response: str
    ) -> None:
        """
        Update conversation history for a user
        """
        if user_phone not in self.conversation_context:
            self.conversation_context[user_phone] = {
                'messages': [],
                'last_updated': datetime.utcnow()
            }
        
        # Add message and response to history
        history = self.conversation_context[user_phone]['messages']
        history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.utcnow()
        })
        history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.utcnow()
        })
        
        # Keep only last 10 messages for context
        self.conversation_context[user_phone]['messages'] = history[-self.MAX_HISTORY:]

    def _create_chat_prompt(self, message: str, context: Dict) -> str:
        """
        Create a prompt for the AI including relevant context
        """
        # Start with the base prompt
        base_prompt = (
            "You are a helpful assistant that helps users interact with their recorded thoughts. "
            "Respond in a natural, conversational way. "
        )

        # Add conversation history context if available
        if context.get('messages'):
            recent_messages = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in context['messages'][-3:]  # Last 3 messages
            ])
            base_prompt += f"\nRecent conversation:\n{recent_messages}\n"

        # Add the current message
        base_prompt += f"\nCurrent message: {message}"
        
        return base_prompt

    def _format_context(self, context: Dict) -> str:
        """
        Format conversation context for the AI
        """
        if not context.get('messages'):
            return ""

        formatted_context = []
        for msg in context['messages'][-3:]:  # Last 3 messages
            role = "User" if msg['role'] == 'user' else "Assistant"
            formatted_context.append(f"{role}: {msg['content']}")

        return "\n".join(formatted_context)