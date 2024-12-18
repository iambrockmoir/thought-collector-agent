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
    def __init__(self, twilio_client, phone_number: str, audio_service=None, storage_service=None, chat_service=None):
        self.client = twilio_client
        self.phone_number = phone_number
        self.audio = audio_service
        self.storage = storage_service
        self.chat = chat_service
        logger.info(f"SMS service initialized with phone number: {phone_number}")

    async def handle_message(self, from_number: str, message: str, media_url: Optional[str] = None, content_type: Optional[str] = None) -> None:
        """Handle incoming SMS message"""
        try:
            if media_url:
                # Handle audio message
                logger.info(f"Processing audio from {from_number}...")
                transcription = await self.audio.process_audio(media_url, content_type)
                
                if not transcription:
                    logger.error("Failed to get transcription from audio")
                    return
                
                # Store the transcribed message
                await self.storage.store_chat_message(
                    message=transcription,
                    from_number=from_number
                )
                
                # Process the transcribed message
                response = await self.chat.process_message(
                    message=transcription,
                    user_phone=from_number
                )
                
                # Send the response via SMS
                logger.info(f"Sending SMS response to {from_number}: {response}")
                await self.send_message(to=from_number, body=response)
                
                return response
            else:
                # Handle text message
                logger.info(f"Processing text from {from_number}: {message}...")
                response = await self.chat.process_message(
                    message=message,
                    user_phone=from_number
                )
                
                # Send the response via SMS
                logger.info(f"Sending SMS response to {from_number}: {response}")
                await self.send_message(to=from_number, body=response)
                
                return response
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
            await self.storage.store_thought(from_number, audio_transcribed)
            
            # Send confirmation
            await self.send_sms(
                from_number,
                "I've recorded your thought! Here's what I heard: " + audio_transcribed
            )
        except Exception as e:
            logger.error(f"Failed to handle audio message: {str(e)}")
            raise

    async def send_sms(self, to_number: str, message: str) -> None:
        """Send SMS message"""
        try:
            logger.info(f"Sending SMS response: {message[:20]}...")
            self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
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
            message = self.client.messages.create(
                to=to,
                from_=self.phone_number,
                body=body
            )
            logger.info(f"Message sent successfully: {message.sid}")
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            raise
