from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile
import mimetypes
import os

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Request OGG format
            ogg_url = media_url + ".ogg"
            print(f"DEBUG: Downloading OGG from: {ogg_url}")
            
            response = requests.get(
                ogg_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                headers={'Accept': 'audio/ogg'}
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                print(f"ERROR: Response content: {response.content[:200]}")
                raise Exception(f"Failed to download audio: {response.status_code}")
            
            # Save the OGG file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as audio_file:
                audio_file.write(response.content)
                audio_path = audio_file.name
                print(f"DEBUG: Saved OGG file to: {audio_path}")
                
                # Print file info
                file_size = os.path.getsize(audio_path)
                mime_type = mimetypes.guess_type(audio_path)[0]
                print(f"DEBUG: File size: {file_size} bytes")
                print(f"DEBUG: MIME type: {mime_type}")
            
            print("DEBUG: Transcribing with Whisper API")
            # Use OpenAI's Whisper API
            with open(audio_path, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            # Clean up
            os.remove(audio_path)
            
            print(f"DEBUG: Transcription result: {transcript}")
            return {
                "transcription": transcript,
                "message": f"I heard: {transcript}"
            }
            
        except Exception as e:
            print(f"Error processing audio: {str(e)}")
            return {
                "transcription": "",
                "message": "Sorry, I couldn't process that audio. Please try again. For best results, please record in a quiet environment and speak clearly."
            }