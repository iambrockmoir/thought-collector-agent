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
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )

    def _send_sms(self, to_number: str, message: str):
        """Send SMS using Twilio"""
        try:
            self.client.messages.create(
                body=message,
                from_=os.getenv('TWILIO_PHONE_NUMBER'),
                to=to_number
            )
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")

    def handle_text_message(self, from_number: str, body: str) -> str:
        """Handle incoming text message"""
        try:
            logger.info(f"Processing text from {from_number}: {body[:50]}...")
            
            # Process message through chat service synchronously
            chat_response = asyncio.run(self.chat.process_message(from_number, body))
            
            logger.info(f"Sending SMS response: {chat_response[:50]}...")
            self._send_sms(from_number, chat_response)
            return chat_response
            
        except Exception as e:
            logger.error(f"Failed to handle text message: {str(e)}")
            error_msg = "Sorry, I encountered an error. Please try again."
            self._send_sms(from_number, error_msg)
            return str(e)

    def process_message(self, from_number: str, body: str = None, media_url: str = None) -> str:
        """Process incoming SMS message"""
        try:
            if media_url:
                return self.handle_audio_message(from_number, media_url)
            else:
                return self.handle_text_message(from_number, body)
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            return str(e)

    def _send_message(self, to: str, body: str):
        """Helper to send Twilio message"""
        return self.client.messages.create(
            to=to,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            body=body
        )

    def handle_audio_message(self, from_number: str, media_url: str) -> str:
        """Handle incoming audio message"""
        try:
            logger.info(f"Processing audio from {from_number}")
            
            # Process audio through audio service
            transcription = self.audio.process_audio(media_url)
            logger.info(f"Audio transcribed: {transcription}")
            
            # Store the transcription
            self.storage.store_thought(from_number, transcription)
            
            # Send confirmation
            response = "Got it! I've stored your thought."
            self._send_sms(from_number, response)
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle audio message: {str(e)}")
            error_msg = "Sorry, I had trouble processing your audio. Please try again."
            self._send_sms(from_number, error_msg)
            return str(e)
