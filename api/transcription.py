from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile
from pydub import AudioSegment
import os

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Downloading audio from {media_url}")
            # Download audio file
            response = requests.get(media_url)
            
            # Save the AMR file
            with tempfile.NamedTemporaryFile(suffix='.amr', delete=False) as amr_file:
                amr_file.write(response.content)
                amr_path = amr_file.name
            
            print("DEBUG: Converting AMR to MP3")
            # Convert AMR to MP3
            audio = AudioSegment.from_file(amr_path, format="amr")
            mp3_path = amr_path.replace('.amr', '.mp3')
            audio.export(mp3_path, format="mp3")
            
            print("DEBUG: Transcribing with Whisper API")
            # Use OpenAI's Whisper API
            with open(mp3_path, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Clean up temporary files
            os.remove(amr_path)
            os.remove(mp3_path)
            
            print(f"DEBUG: Transcription result: {transcript.text}")
            return {
                "transcription": transcript.text,
                "message": f"I heard: {transcript.text}"
            }
            
        except Exception as e:
            print(f"Error processing audio: {str(e)}")
            return {
                "transcription": "",
                "message": "Sorry, I couldn't process that audio. Please try again."
            }