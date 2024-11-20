import logging
import requests
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, openai_client: OpenAI, converter_url: str):
        self.client = openai_client
        self.converter_url = converter_url

    def process_audio(self, audio_data: bytes, auth: tuple) -> tuple[str, bool]:
        """
        Process audio data and return transcription
        Returns: (message, success)
        """
        try:
            # Save the audio file
            with open("/tmp/original_audio.amr", "wb") as f:
                f.write(audio_data)
                
            # Convert audio
            with open("/tmp/original_audio.amr", "rb") as audio_file:
                files = {'audio': ('audio.amr', audio_file, 'audio/amr')}
                converter_response = requests.post(
                    self.converter_url,
                    files=files,
                    timeout=30
                )
                
            if converter_response.status_code != 200:
                logger.error(f"Converter failed: {converter_response.status_code}")
                return "Sorry, I had trouble converting your audio.", False
                
            # Save converted audio
            with open("/tmp/audio.mp3", "wb") as f:
                f.write(converter_response.content)
            
            # Transcribe
            with open("/tmp/audio.mp3", "rb") as f:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            
            return transcript.text, True
            
        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            return "Sorry, something went wrong processing your audio.", False
