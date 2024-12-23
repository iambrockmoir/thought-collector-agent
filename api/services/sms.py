import logging
import requests
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional, Tuple
from twilio.rest import Client
import os
import hashlib
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self, twilio_client, phone_number: str, audio_service=None, storage_service=None, chat_service=None, tag_service=None):
        self.client = twilio_client
        self.phone_number = phone_number
        self.audio = audio_service
        self.storage = storage_service
        self.chat = chat_service
        self.tags = tag_service
        logger.info(f"SMS service initialized with phone number: {phone_number}")

    async def handle_message(self, from_number: str, message: str, media_url: Optional[str] = None, content_type: Optional[str] = None) -> None:
        """Handle incoming SMS message"""
        try:
            # Check for pending tag confirmation
            pending_thought_id = self._get_pending_thought(from_number)
            
            if pending_thought_id and not media_url:
                # This is a tag confirmation message
                if message.lower() == 'skip':
                    del self._pending_thoughts[from_number]
                    await self.send_sms(from_number, "Skipped tagging. Your thought has been saved!")
                    return
                
                # Process tag confirmation
                confirmed_tags = await self.tags.process_tag_confirmation(message)
                await self.tags.store_thought_tags(pending_thought_id, confirmed_tags, from_number)
                
                del self._pending_thoughts[from_number]
                await self.send_sms(
                    from_number,
                    f"Tags added: {', '.join(confirmed_tags)}\nYour thought has been saved!"
                )
                return
            
            # Handle normal message flow
            if media_url:
                # Handle audio message
                return await self.handle_audio_message(from_number, media_url, content_type)
            else:
                # Handle text message
                return await self.handle_text_message(from_number, message)
        except Exception as e:
            logger.error(f"Failed to handle message: {str(e)}")
            raise

    async def handle_text_message(self, from_number: str, message: str) -> None:
        """Handle text message"""
        try:
            logger.info(f"Processing text from {from_number}: {message}...")
            response = await self.chat.process_message(from_number, message)
            await self.send_sms(from_number, response)
        except Exception as e:
            logger.error(f"Failed to handle text message: {str(e)}")
            raise

    async def handle_audio_message(self, from_number: str, media_url: str, content_type: str) -> None:
        """Handle audio message"""
        try:
            logger.info(f"Processing audio from {from_number}")
            audio_transcribed = await self.audio.process_audio(media_url, content_type)
            logger.info(f"Audio transcribed: {audio_transcribed}")
            
            # Store the transcribed thought
            thought_data = await self.storage.store_thought(from_number, audio_transcribed)
            thought_id = thought_data['id']
            
            # Generate tag suggestions
            suggested_tags = await self.tags.suggest_tags(audio_transcribed, from_number)
            
            # Send transcription and tag suggestions
            await self.send_sms(
                from_number,
                f"I've recorded your thought! Here's what I heard: {audio_transcribed}\n\n" +
                f"Suggested tags: {', '.join(suggested_tags)}\n" +
                "Reply with your chosen tags (comma-separated) or 'skip' to skip tagging."
            )
            
            # Store the thought ID in temporary storage for tag confirmation
            self._store_pending_thought(from_number, thought_id)
            
        except Exception as e:
            logger.error(f"Failed to handle audio message: {str(e)}")
            raise

    async def send_sms(self, to_number: str, message: str) -> None:
        """Send SMS message"""
        try:
            logger.info(f"Sending SMS response: {message[:20]}...")
            # Run Twilio API call in an executor to prevent blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    body=message,
                    from_=self.phone_number,
                    to=to_number
                )
            )
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            raise

    async def send_error_message(self, to_number: str) -> None:
        """Send error message"""
        try:
            await self.send_sms(
                to_number,
                "Sorry, I encountered an error processing your message. Please try again."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {str(e)}")
            # Don't raise here to avoid error cascade

    async def send_message(self, to: str, body: str) -> None:
        """Send an SMS message using Twilio"""
        try:
            logger.info(f"Sending message to {to}")
            # Run Twilio API call in an executor to prevent blocking
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    body=body,
                    from_=self.phone_number,
                    to=to
                )
            )
            logger.info(f"Message sent successfully: {message.sid}")
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            raise

    def _store_pending_thought(self, user_phone: str, thought_id: str) -> None:
        """Store thought ID waiting for tag confirmation."""
        # You might want to use a proper temporary storage solution in production
        if not hasattr(self, '_pending_thoughts'):
            self._pending_thoughts = {}
        self._pending_thoughts[user_phone] = {
            'thought_id': thought_id,
            'timestamp': datetime.now()
        }

    def _get_pending_thought(self, user_phone: str) -> Optional[str]:
        """Get pending thought ID for tag confirmation."""
        if not hasattr(self, '_pending_thoughts'):
            return None
        
        pending = self._pending_thoughts.get(user_phone)
        if not pending:
            return None
            
        # Check if the pending thought is still valid (within 5 minutes)
        if datetime.now() - pending['timestamp'] > timedelta(minutes=5):
            del self._pending_thoughts[user_phone]
            return None
            
        return pending['thought_id']
