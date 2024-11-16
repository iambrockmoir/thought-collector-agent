from typing import Dict, Any
from lib.twilio_client import TwilioClient
from lib.error_handler import ErrorHandler, AppError
from api.chat import ChatEngine
from api.transcription import AudioProcessor
from lib.config import get_settings

settings = get_settings()

class SMSHandler:
    def __init__(self):
        self.twilio_client = TwilioClient()
        self.error_handler = ErrorHandler()
        self.chat_engine = ChatEngine()
        self.audio_processor = AudioProcessor()

    async def handle_incoming_message(self, webhook_data: Dict[str, Any]) -> str:
        """Handle incoming SMS webhook from Twilio"""
        try:
            num_media = int(webhook_data.get('NumMedia', ['0'])[0])
            from_number = webhook_data.get('From', [''])[0]

            if num_media > 0:
                return await self.handle_audio_message(webhook_data)
            else:
                return await self.handle_text_message(webhook_data)

        except Exception as e:
            error_message = self.error_handler.handle_sms_error(e)
            return self._create_twiml_response(error_message)

    async def handle_audio_message(self, webhook_data: Dict[str, Any]) -> str:
        """Handle incoming audio message"""
        try:
            # Extract message details
            from_number = webhook_data.get('From', [''])[0]
            media_url = webhook_data.get('MediaUrl0', [''])[0]
            content_type = webhook_data.get('MediaContentType0', [''])[0]

            # Validate media type
            if not content_type.startswith('audio/'):
                return self._create_twiml_response(
                    "Sorry, I can only process audio messages. Please send a voice recording."
                )

            # Process audio
            auth = (settings.twilio_account_sid, settings.twilio_auth_token)
            result = await self.audio_processor.process_audio_message(
                media_url=media_url,
                user_phone=from_number,
                auth=auth
            )

            return self._create_twiml_response(result['message'])

        except Exception as e:
            error_message = self.error_handler.handle_sms_error(e)
            return self._create_twiml_response(error_message)

    async def handle_text_message(self, webhook_data: Dict[str, Any]) -> str:
        """Handle incoming text message"""
        try:
            message = webhook_data.get('Body', [''])[0]
            from_number = webhook_data.get('From', [''])[0]

            # Check for commands
            if message.lower().strip() == 'recent':
                # Get recent thoughts
                recent_thoughts = self.audio_processor.get_recent_thoughts(from_number)
                if not recent_thoughts:
                    return self._create_twiml_response(
                        "You haven't recorded any thoughts yet. Send me a voice message to get started!"
                    )
                
                # Format recent thoughts
                thoughts_text = "\n\n".join([
                    f"📝 {i+1}. {thought['transcription'][:100]}..."
                    for i, thought in enumerate(recent_thoughts)
                ])
                return self._create_twiml_response(
                    f"Your recent thoughts:\n{thoughts_text}"
                )

            # Process as normal chat message
            response = await self.chat_engine.process_query(
                user_phone=from_number,
                message=message
            )

            return self._create_twiml_response(response)

        except Exception as e:
            error_message = self.error_handler.handle_sms_error(e)
            return self._create_twiml_response(error_message)

    def _create_twiml_response(self, message: str) -> str:
        """Create TwiML response"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
                  <Response>
                      <Message>{message}</Message>
                  </Response>"""