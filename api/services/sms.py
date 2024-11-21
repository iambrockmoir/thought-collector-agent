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
    def __init__(self, chat_service, audio_service, storage_service):
        self.chat = chat_service
        self.audio = audio_service
        self.storage = storage_service
        self.twilio_client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )

    def handle_incoming_message(self, from_number: str, body: str, media_url: str = None, content_type: str = None):
        """Handle incoming SMS/MMS message"""
        try:
            if media_url and 'audio' in content_type:
                logger.info(f"Processing audio from {from_number}")
                transcription = self.audio.process_audio(media_url, content_type)
                
                if transcription:
                    logger.info(f"Audio transcribed: {transcription[:50]}...")
                    thought_id = self.storage.store_thought(from_number, media_url, transcription)
                    
                    response = MessagingResponse()
                    response.message("✓ Thought recorded")
                    return str(response)
                else:
                    response = MessagingResponse()
                    response.message("Sorry, I couldn't process that audio. Please try again.")
                    return str(response)
            else:
                return self.handle_text_message(from_number, body)
            
        except Exception as e:
            logger.error(f"Failed to handle message: {str(e)}", exc_info=True)
            response = MessagingResponse()
            response.message("Sorry, I encountered an error. Please try again.")
            return str(response)

    def handle_text_message(self, from_number: str, body: str):
        """Handle incoming text message"""
        try:
            logger.info(f"Processing text from {from_number}: {body[:50]}...")
            
            chat_response = self.chat.process_message(body, from_number)
            
            logger.info(f"Sending SMS response: {chat_response[:50]}...")
            response = MessagingResponse()
            response.message(chat_response)
            return str(response)
            
        except Exception as e:
            logger.error(f"Failed to handle text message: {str(e)}", exc_info=True)
            response = MessagingResponse()
            response.message("Sorry, I encountered an error. Please try again.")
            return str(response)

    def _send_message(self, to: str, body: str):
        """Helper to send Twilio message"""
        return self.twilio_client.messages.create(
            to=to,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            body=body
        )
