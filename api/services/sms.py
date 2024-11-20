import logging
import requests
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional, Tuple
from twilio.rest import Client

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self, twilio_auth: tuple, audio_service, chat_service, storage_service):
        self.client = Client(*twilio_auth)
        self.audio = audio_service
        self.chat = chat_service
        self.storage = storage_service

    async def handle_incoming_message(self, from_number: str, body: str, media_url: str = None, content_type: str = None):
        """Handle incoming SMS/MMS message"""
        try:
            if media_url and 'audio' in content_type:
                logger.info(f"Processing audio from {from_number}")
                transcription = await self.audio.process_audio(media_url, content_type)
                
                if transcription:
                    logger.info(f"Audio transcribed: {transcription[:50]}...")
                    thought_id = self.storage.store_thought(from_number, media_url, transcription)
                    return self._send_message(
                        to=from_number,
                        body=f"✓ Thought recorded: {transcription[:100]}..."
                    )
                else:
                    return self._send_message(
                        to=from_number,
                        body="Sorry, I couldn't process that audio. Could you try sending it again?"
                    )
            else:
                logger.info(f"Processing text from {from_number}: {body[:50]}...")
                response = self.chat.process_message(body, from_number)
                return self._send_message(to=from_number, body=response)
                
        except Exception as e:
            logger.error(f"Failed to handle message: {str(e)}", exc_info=True)
            return self._send_message(
                to=from_number,
                body="Sorry, I encountered an error. Please try again."
            )

    def _send_message(self, to: str, body: str):
        """Send a Twilio response"""
        resp = MessagingResponse()
        resp.message(body)
        return str(resp), 200, {'Content-Type': 'text/xml'}
