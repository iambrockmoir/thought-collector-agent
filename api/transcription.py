import tempfile
import os
from pydub import AudioSegment
import logging
import requests
from typing import Dict, Optional
from datetime import datetime
from lib.openai_client import OpenAIClient
from lib.error_handler import AppError
from lib.config import get_settings
import io

settings = get_settings()
logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.transcriptions = {}

    async def process_audio_message(
        self,
        media_url: str,
        user_phone: str,
        auth: tuple
    ) -> Dict[str, str]:
        """Process audio from Twilio media URL"""
        temp_amr = None
        temp_mp3 = None
        
        try:
            logger.info(f"Downloading audio from URL: {media_url}")
            # Download audio file from Twilio
            audio_content = self.download_audio(media_url, auth)
            
            # Save the AMR file first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.amr') as temp:
                temp.write(audio_content)
                temp_amr = temp.name
                logger.info(f"Saved AMR audio to temporary file: {temp_amr}")
            
            # Convert AMR to MP3
            temp_mp3 = temp_amr.replace('.amr', '.mp3')
            logger.info("Converting AMR to MP3...")
            audio = AudioSegment.from_file(temp_amr)
            audio.export(temp_mp3, format="mp3")
            logger.info(f"Converted audio saved to: {temp_mp3}")

            try:
                # Transcribe audio
                logger.info("Starting transcription...")
                transcription = await self.openai_client.transcribe_audio(temp_mp3)
                logger.info("Transcription completed")
                
                # Store transcription
                if user_phone not in self.transcriptions:
                    self.transcriptions[user_phone] = []
                
                thought_record = {
                    'transcription': transcription,
                    'timestamp': datetime.utcnow().isoformat(),
                    'audio_url': media_url
                }
                
                self.transcriptions[user_phone].append(thought_record)
                logger.info("Thought record stored in memory")

                # Create user-friendly response
                short_transcription = (
                    transcription[:100] + '...' 
                    if len(transcription) > 100 
                    else transcription
                )
                
                return {
                    'status': 'success',
                    'transcription': transcription,
                    'message': f"✓ Thought recorded! Here's what I heard:\n{short_transcription}"
                }

            finally:
                # Clean up temporary files
                for temp_file in [temp_amr, temp_mp3]:
                    if temp_file and os.path.exists(temp_file):
                        logger.info(f"Cleaning up temporary file: {temp_file}")
                        os.unlink(temp_file)

        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            # Clean up temporary files in case of error
            for temp_file in [temp_amr, temp_mp3]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            raise AppError(f"Audio processing failed: {str(e)}", status_code=500)

    def download_audio(self, media_url: str, auth: tuple) -> bytes:
        """Download audio file from Twilio's media URL"""
        try:
            logger.info(f"Downloading audio from {media_url}")
            response = requests.get(media_url, auth=auth)
            response.raise_for_status()
            logger.info("Audio download successful")
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download audio: {str(e)}")
            raise AppError(f"Failed to download audio: {str(e)}", status_code=500)

    def get_recent_thoughts(self, user_phone: str, limit: int = 5) -> list:
        """Get recent thoughts for a user"""
        user_thoughts = self.transcriptions.get(user_phone, [])
        return sorted(
            user_thoughts,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]