from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import requests
from typing import Optional
import logging
from lib.config import get_settings
from lib.error_handler import AppError

settings = get_settings()
logger = logging.getLogger(__name__)

class TwilioClient:
    def __init__(self):
        try:
            self.client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
            self.phone_number = settings.twilio_phone_number
            # Verify credentials
            self.client.api.accounts(settings.twilio_account_sid).fetch()
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {str(e)}")
            raise AppError("Failed to initialize messaging service")

    def send_message(self, to_number: str, message: str) -> str:
        """Send an SMS message and return the message SID."""
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            logger.info(f"Message sent successfully to {to_number}")
            return message.sid
        except TwilioRestException as e:
            logger.error(f"Twilio error sending message: {str(e)}")
            if e.code == 21608:  # Unverified number
                raise AppError("This phone number is not verified with our test account.")
            elif e.code == 21211:  # Invalid phone number
                raise AppError("Invalid phone number format.")
            else:
                raise AppError(f"Failed to send message: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error sending message: {str(e)}")
            raise AppError("An unexpected error occurred while sending the message.")

    def download_audio(self, media_url: str) -> bytes:
        """Download audio file from Twilio's media URL."""
        try:
            response = requests.get(
                media_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download audio: {str(e)}")
            raise AppError("Failed to download audio file")