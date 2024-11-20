import logging
import requests
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self, twilio_auth: tuple, audio_service, chat_service, storage_service=None):
        self.twilio_auth = twilio_auth  # (account_sid, auth_token)
        self.audio_service = audio_service
        self.chat_service = chat_service
        self.storage = storage_service

    def handle_incoming_message(self, 
                              from_number: str, 
                              body: str,
                              media_url: Optional[str] = None,
                              content_type: Optional[str] = None) -> Tuple[str, int, dict]:
        """
        Handle incoming SMS webhook from Twilio
        Returns: (response_text, status_code, headers)
        """
        try:
            # Handle audio messages
            if content_type and media_url:
                logger.info(f"Processing audio from {from_number}")
                return self._handle_audio_message(from_number, media_url)
                
            # Handle text messages
            elif body:
                logger.info(f"Processing text from {from_number}: {body[:50]}...")
                return self._handle_text_message(from_number, body)
            
            else:
                logger.warning("Received message with no content")
                return '', 200, {}
                
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            return self._create_response("Sorry, something went wrong.")

    def _handle_audio_message(self, from_number: str, media_url: str) -> Tuple[str, int, dict]:
        """Process audio message and return Twilio response"""
        try:
            # Download from Twilio
            audio_response = requests.get(media_url, auth=self.twilio_auth, timeout=30)
            
            if audio_response.status_code != 200:
                return self._create_response("Sorry, I couldn't download your audio.")
                
            # Process audio
            transcribed_text, success = self.audio_service.process_audio(
                audio_response.content, 
                self.twilio_auth
            )
            
            if not success:
                return self._create_response(transcribed_text)  # Error message
                
            # Store thought if storage available
            if self.storage:
                self.storage.store_thought(
                    phone_number=from_number,
                    audio_url=media_url,
                    transcription=transcribed_text
                )
            
            return self._create_response("Thought saved!")
            
        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            return self._create_response("Sorry, something went wrong processing your audio.")

    def _handle_text_message(self, from_number: str, body: str) -> Tuple[str, int, dict]:
        """Process text message and return Twilio response"""
        response = self.chat_service.process_message(body, from_number)
        return self._create_response(response)

    def _create_response(self, message: str) -> Tuple[str, int, dict]:
        """Create a Twilio response"""
        resp = MessagingResponse()
        resp.message(message)
        return str(resp), 200, {'Content-Type': 'text/xml'}
