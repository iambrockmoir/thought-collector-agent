from typing import Dict, Any
import requests
import openai
from lib.config import get_settings

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            # Download audio file
            response = requests.get(media_url)
            
            # Use OpenAI's Whisper API directly
            with open("/tmp/audio.mp3", "wb") as f:
                f.write(response.content)
            
            with open("/tmp/audio.mp3", "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
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