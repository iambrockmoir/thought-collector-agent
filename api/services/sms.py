import logging
import requests
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional, Tuple
from twilio.rest import Client
import os

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self, twilio_auth: tuple, audio_service, chat_service, storage_service):
        self.client = Client(*twilio_auth)
        self.audio = audio_service
        self.chat = chat_service
        self.storage = storage_service

    async def handle_incoming_message(self, from_number: str, body: str, media_url: str = None, content_type: str = None):
        """Handle incoming SMS/MMS message asynchronously"""
        try:
            if media_url and 'audio' in content_type:
                logger.info(f"Processing audio from {from_number}")
                transcription = await self.audio.process_audio(media_url, content_type)
                
                if transcription:
                    logger.info(f"Audio transcribed: {transcription[:50]}...")
                    thought_id = self.storage.store_thought(from_number, media_url, transcription)
                    
                    # Simple confirmation response
                    response = MessagingResponse()
                    response.message("✓ Thought recorded")
                    return response
                else:
                    response = MessagingResponse()
                    response.message("Sorry, I couldn't process that audio. Please try again.")
                    return response
            
            return MessagingResponse().message(
                "Sorry, I encountered an error. Please try again."
            )
            
        except Exception as e:
            logger.error(f"Failed to handle message: {str(e)}", exc_info=True)
            return MessagingResponse().message(
                "Sorry, I encountered an error. Please try again."
            )

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
