import logging
import tempfile
import aiohttp
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, openai_client: OpenAI, converter_url: str):
        self.client = openai_client
        self.converter_url = converter_url
        self.timeout = 25

    async def process_audio(self, audio_url: str, content_type: str) -> Optional[str]:
        """Process audio and return transcription"""
        try:
            logger.info(f"Starting audio processing for {audio_url}")
            logger.info(f"Content type: {content_type}")
            
            # Download audio file
            logger.info("Downloading audio file...")
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    audio_data = await response.read()
            logger.info("Audio file downloaded")

            # Convert using Rails service
            logger.info(f"Converting audio using service at {self.converter_url}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.converter_url,
                    data={'audio': audio_data, 'content_type': content_type}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Converter service error: {error_text}")
                        raise Exception(f"Converter service returned {response.status}")
                    
                    converted_data = await response.read()
                    logger.info("Audio successfully converted")

            # Transcribe with OpenAI
            logger.info("Transcribing with OpenAI...")
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                temp_file.write(converted_data)
                temp_file.flush()
                
                with open(temp_file.name, 'rb') as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
            
            logger.info(f"Transcription complete: {response[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process audio: {str(e)}", exc_info=True)
            return None
