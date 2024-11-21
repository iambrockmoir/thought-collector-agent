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

    async def handle_text_message(self, from_number: str, body: str) -> str:
        """Handle incoming text message"""
        try:
            logger.info(f"Processing text from {from_number}: {body[:50]}...")
            
            # Process message through chat service
            chat_response = await self.chat.process_message(from_number, body)
            
            logger.info(f"Sending SMS response: {chat_response[:50]}...")
            self._send_sms(from_number, chat_response)
            return chat_response
            
        except Exception as e:
            logger.error(f"Failed to handle text message: {str(e)}")
            self._send_sms(from_number, "Sorry, I encountered an error. Please try again.")
            return str(e)

    async def process_message(self, from_number: str, body: str = None, media_url: str = None) -> str:
        """Process incoming SMS message"""
        try:
            if media_url:
                return await self.handle_audio_message(from_number, media_url)
            else:
                return await self.handle_text_message(from_number, body)
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
