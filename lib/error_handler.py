from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500, user_message: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.user_message = user_message or "An error occurred. Please try again later."
        super().__init__(self.message)

class ErrorHandler:
    @staticmethod
    def handle_transcription_error(error: Exception) -> str:
        logger.error(f"Transcription error: {str(error)}")
        return "Sorry, I couldn't transcribe your audio. Please try sending it again."

    @staticmethod
    def handle_storage_error(error: Exception) -> str:
        logger.error(f"Storage error: {str(error)}")
        return "There was an issue saving your thought. Please try again."

    @staticmethod
    def handle_sms_error(error: Exception) -> str:
        logger.error(f"SMS error: {str(error)}")
        return "Message couldn't be sent. Please try again later."