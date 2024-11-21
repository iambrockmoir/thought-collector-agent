import logging
import tempfile
import aiohttp
import os
from typing import Optional
from openai import OpenAI
import requests

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.converter_url = os.getenv('AUDIO_CONVERTER_URL', '')
        # Get Twilio credentials
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        logger.info(f"Audio service initialized with converter URL: {self.converter_url}")

    def process_audio_sync(self, audio_url: str, content_type: str) -> str:
        """Process audio file synchronously and return transcription"""
        try:
            # Download AMR file from Twilio with authentication
            logger.info(f"Downloading audio from {audio_url}")
            amr_response = requests.get(
                audio_url,
                auth=(self.twilio_account_sid, self.twilio_auth_token)
            )
            
            if amr_response.status_code != 200:
                logger.error(f"Failed to download audio from Twilio: {amr_response.status_code}")
                return None
                
            amr_data = amr_response.content
            logger.info(f"Downloaded {len(amr_data)} bytes of audio data")
            
            # Convert AMR to MP3 using conversion service
            logger.info(f"Converting AMR to MP3...")
            files = {'audio': ('audio.amr', amr_data, 'audio/amr')}
            
            logger.info(f"Making conversion request to: {self.converter_url}")
            conversion_response = requests.post(
                self.converter_url,
                files=files,
                timeout=30
            )
            
            if conversion_response.status_code != 200:
                logger.error(f"Conversion failed with status {conversion_response.status_code}: {conversion_response.text}")
                logger.error(f"Response headers: {conversion_response.headers}")
                return None
                
            # Get MP3 data from conversion service
            mp3_data = conversion_response.content
            logger.info(f"Received converted MP3 data: {len(mp3_data)} bytes")
            
            # Save MP3 temporarily
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(mp3_data)
                temp_path = temp_file.name

            # Transcribe MP3
            logger.info("Transcribing audio with OpenAI Whisper...")
            with open(temp_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            # Cleanup
            os.unlink(temp_path)
            logger.info("Transcription complete")
            
            return transcript.text

        except Exception as e:
            logger.error(f"Failed to process audio: {str(e)}", exc_info=True)
            return None

    async def process_audio(self, audio_url: str, content_type: str) -> Optional[str]:
        """Process audio and return transcription"""
        try:
            logger.info(f"Starting audio processing for {audio_url}")
            logger.info(f"Content type: {content_type}")
            
            # Download audio file with Twilio credentials
            logger.info("Downloading audio file...")
            auth = aiohttp.BasicAuth(
                login=os.getenv('TWILIO_ACCOUNT_SID'),
                password=os.getenv('TWILIO_AUTH_TOKEN')
            )
            
            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download audio: {response.status}")
                        logger.error(await response.text())
                        return None
                    audio_data = await response.read()
                    logger.info(f"Audio file downloaded: {len(audio_data)} bytes")
                    logger.info(f"File header: {audio_data[:20].hex()}")

            # Convert using Rails service
            logger.info(f"Converting audio using service at {self.converter_url}")
            
            # Create form data matching multer's expectations
            data = aiohttp.FormData()
            data.add_field('audio',  # Must match multer's upload.single('audio')
                          audio_data,
                          filename='audio.amr',  # Original filename
                          content_type='audio/amr')

            async with aiohttp.ClientSession() as session:
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

            # Transcribe with OpenAI
            logger.info("Transcribing with OpenAI...")
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                temp_file.write(converted_data)
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
            
        except Exception as e:
            logger.error(f"Failed to process audio: {str(e)}", exc_info=True)
            return None
