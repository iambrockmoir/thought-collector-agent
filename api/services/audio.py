import logging
import tempfile
import aiohttp
import os
from typing import Optional
from openai import OpenAI
import requests
import asyncio
from api.config import get_settings

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, openai_client, converter_url: str):
        self.client = openai_client
        self.converter_url = converter_url
        self.base_url = os.getenv('BASE_URL')
        logger.info(f"Audio service initialized with converter URL: {converter_url}")

    async def process_audio(self, url: str, content_type: str, from_number: str) -> Optional[str]:
        """Process audio file from URL and return transcription"""
        try:
            if not content_type:
                logger.error("No content type provided")
                return None
            
            # Create aiohttp session for async requests
            async with aiohttp.ClientSession() as session:
                # Download audio with Twilio auth
                audio_data = await self._download_audio(session, url)
                if not audio_data:
                    return None
                
                # Convert to MP3 with timeout
                mp3_data = await self._convert_audio(session, audio_data, timeout=25, from_number=from_number)
                if not mp3_data:
                    return None
                
                # Transcribe with timeout
                return await asyncio.wait_for(
                    self._transcribe_audio(mp3_data, timeout=None),
                    timeout=25
                )
                
        except asyncio.TimeoutError:
            logger.error("Audio processing timed out")
            return "I'm sorry, but the audio message took too long to process. Could you try sending a shorter message or sending your thought as text?"
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
            return audio_data

    async def _convert_audio(self, session, audio_data, timeout, from_number):
        # Convert using Rails service
        logger.info(f"Converting audio using service at {self.converter_url}")
        
        # Create form data matching multer's expectations
        data = aiohttp.FormData()
        data.add_field('audio',
                      audio_data,
                      filename='audio.amr',
                      content_type='audio/amr')
        data.add_field('callback_url', f"{self.base_url}/audio-callback")
        data.add_field('from_number', from_number)

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

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Convert content type to file extension"""
        content_type_map = {
            'audio/amr': 'amr',
            'audio/amr-wb': 'amr',
            'audio/mp3': 'mp3',
            'audio/mpeg': 'mp3',
            'audio/ogg': 'ogg',
            'audio/wav': 'wav',
            'audio/x-wav': 'wav',
            'audio/webm': 'webm',
            'audio/aac': 'aac',
            'audio/m4a': 'm4a',
        }
        
        if not content_type:
            logger.error("No content type provided")
            return 'amr'  # Default to AMR as Twilio commonly uses this
        
        extension = content_type_map.get(content_type.lower())
        if not extension:
            logger.warning(f"Unknown content type: {content_type}, defaulting to amr")
            return 'amr'
        
        return extension
