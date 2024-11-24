import logging
import tempfile
import aiohttp
import os
from typing import Optional
from openai import OpenAI
import requests
import asyncio

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, openai_client, converter_url: str):
        self.client = openai_client
        self.converter_url = converter_url
        logger.info(f"Audio service initialized with converter URL: {converter_url}")

    async def process_audio(self, url: str, content_type: Optional[str] = None) -> str:
        try:
            # Download audio file with timeout
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                content_type, audio_data = await self._download_audio(session, url)
                
                # Convert to MP3 with timeout
                mp3_data = await self._convert_audio(session, audio_data, timeout=4)
                
                # Transcribe with timeout
                return await self._transcribe_audio(mp3_data, timeout=4)
                
        except asyncio.TimeoutError:
            logger.error("Audio processing timed out")
            return "I'm sorry, but the audio message was too long to process. Could you try sending a shorter message or sending your thought as text?"
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            return "I apologize, but I encountered an error processing your audio message. Could you try again or send your thought as text?"

    async def _download_audio(self, session, url):
        # Download audio file with Twilio credentials
        logger.info("Downloading audio file...")
        auth = aiohttp.BasicAuth(
            login=os.getenv('TWILIO_ACCOUNT_SID'),
            password=os.getenv('TWILIO_AUTH_TOKEN')
        )
        
        async with session.get(url, auth=auth) as response:
            if response.status != 200:
                logger.error(f"Failed to download audio: {response.status}")
                logger.error(await response.text())
                return None
            audio_data = await response.read()
            logger.info(f"Audio file downloaded: {len(audio_data)} bytes")
            logger.info(f"File header: {audio_data[:20].hex()}")
            return content_type, audio_data

    async def _convert_audio(self, session, audio_data, timeout):
        # Convert using Rails service
        logger.info(f"Converting audio using service at {self.converter_url}")
        
        # Create form data matching multer's expectations
        data = aiohttp.FormData()
        data.add_field('audio',  # Must match multer's upload.single('audio')
                      audio_data,
                      filename='audio.amr',  # Original filename
                      content_type='audio/amr')

        async with session.post(self.converter_url, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Converter service error: {error_text}")
                raise Exception(f"Converter service returned {response.status}")
            
            converted_data = await response.read()
            logger.info(f"Audio successfully converted: {len(converted_data)} bytes")
            
            # Log first few bytes of converted data
            if len(converted_data) > 0:
                logger.info(f"Converted data header: {converted_data[:20].hex()}")

        return converted_data

    async def _transcribe_audio(self, mp3_data, timeout):
        # Transcribe with OpenAI
        logger.info("Transcribing with OpenAI...")
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            temp_file.write(mp3_data)
            temp_file.flush()
            
            # Verify the MP3 file
            logger.info(f"MP3 file size: {os.path.getsize(temp_file.name)} bytes")
            
            with open(temp_file.name, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
        
        logger.info(f"Transcription complete: {response[:50]}...")
        return response
