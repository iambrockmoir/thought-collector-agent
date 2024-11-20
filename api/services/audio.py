import logging
import requests
from datetime import datetime
from openai import OpenAI
import aiohttp
import asyncio
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, openai_client: OpenAI, converter_url: str):
        self.client = openai_client
        self.converter_url = converter_url
        self.timeout = 25  # Set timeout to 25 seconds (Vercel limit is 30)

    async def process_audio(self, audio_url: str, content_type: str) -> Optional[str]:
        """Process audio and return transcription"""
        try:
            logger.info(f"Starting audio processing for {audio_url}")
            logger.info(f"Content type: {content_type}")
            
            # Download and convert audio with timeout
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Download audio file
                logger.info("Downloading audio file...")
                async with session.get(audio_url) as response:
                    audio_data = await response.read()
                logger.info("Audio file downloaded")

                # Convert audio if needed
                if content_type != 'audio/mp3':
                    logger.info("Converting audio to MP3...")
                    async with session.post(
                        self.converter_url,
                        data={'audio': audio_data, 'content_type': content_type}
                    ) as response:
                        audio_data = await response.read()
                    logger.info("Audio converted to MP3")

            # Transcribe with OpenAI
            logger.info("Transcribing with OpenAI...")
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                with open(temp_file.name, 'rb') as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
            
            logger.info(f"Transcription complete: {response[:50]}...")
            return response
            
        except asyncio.TimeoutError:
            logger.error("Audio processing timed out")
            return None
        except Exception as e:
            logger.error(f"Failed to process audio: {str(e)}", exc_info=True)
            return None
