import logging
import requests
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional, Tuple
from twilio.rest import Client
import os
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self, twilio_auth: tuple, audio_service, chat_service, storage_service):
        self.client = Client(*twilio_auth)
        self.audio = audio_service
        self.chat = chat_service
        self.storage = storage_service
        self._recent_messages = {}  # Store recent message hashes

    def _get_message_hash(self, from_number: str, body: str) -> str:
        """Create a hash of the message to detect duplicates"""
        message = f"{from_number}:{body}:{datetime.now().strftime('%Y-%m-%d-%H')}"
        return hashlib.md5(message.encode()).hexdigest()

    def _is_duplicate(self, msg_hash: str) -> bool:
        """Check if we've processed this message recently"""
        now = datetime.now()
        # Clean up old messages
        self._recent_messages = {
            k: v for k, v in self._recent_messages.items() 
            if now - v < timedelta(minutes=1)
        }
        
        if msg_hash in self._recent_messages:
            return True
            
        self._recent_messages[msg_hash] = now
        return False

    async def handle_incoming_message(self, from_number: str, body: str, media_url: str = None, content_type: str = None):
        """Handle incoming SMS/MMS message asynchronously"""
        try:
            # Check for duplicate message
            msg_hash = self._get_message_hash(from_number, body or media_url)
            if self._is_duplicate(msg_hash):
                logger.info("Duplicate message detected, skipping")
                return MessagingResponse()

            if media_url and 'audio' in content_type:
                logger.info(f"Processing audio from {from_number}")
                transcription = await self.audio.process_audio(media_url, content_type)
                
                if transcription:
                    logger.info(f"Audio transcribed: {transcription[:50]}...")
                    thought_id = self.storage.store_thought(from_number, media_url, transcription)
                    
                    response = MessagingResponse()
                    response.message("✓ Thought recorded")
                    return response
                else:
                    response = MessagingResponse()
                    response.message("Sorry, I couldn't process that audio. Please try again.")
                    return response
            
            # Ensure we always return a response
            response = MessagingResponse()
            try:
                chat_response = self.chat.process_message(body, from_number)
                response.message(chat_response)
            except Exception as e:
                logger.error(f"Chat error: {str(e)}", exc_info=True)
                response.message("Sorry, I encountered an error. Please try again.")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle message: {str(e)}", exc_info=True)
            response = MessagingResponse()
            response.message("Sorry, I encountered an error. Please try again.")
            return response

    def handle_text_message(self, from_number: str, body: str):
        """Handle text messages synchronously"""
        try:
            logger.info(f"Processing text from {from_number}: {body[:50]}...")
            response = self.chat.process_message(body, from_number)
            
            # Create TwiML response
            twiml = MessagingResponse()
            twiml.message(response)
            return twiml
            
        except Exception as e:
            logger.error(f"Failed to handle text message: {str(e)}", exc_info=True)
            twiml = MessagingResponse()
            twiml.message("Sorry, I encountered an error. Please try again.")
            return twiml

    def _send_message(self, to: str, body: str):
        """Helper to send Twilio message"""
        return self.client.messages.create(
            to=to,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            body=body
        )
