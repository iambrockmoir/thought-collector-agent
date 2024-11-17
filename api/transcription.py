from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile
from twilio.rest import Client

settings = get_settings()
openai.api_key = settings.openai_api_key
twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Extract SID from the media URL
            media_sid = media_url.split('/')[-1]
            message_sid = media_url.split('/')[-3]
            
            # Get media in MP3 format
            media = twilio_client.messages(message_sid).media(media_sid).fetch()
            mp3_url = f"{media.uri.replace('.json', '')}.mp3"
            
            print(f"DEBUG: Downloading MP3 from: {mp3_url}")
            response = requests.get(
                f"https://api.twilio.com{mp3_url}",
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                raise Exception("Failed to download audio")
            
            # Save the MP3 file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:
                audio_file.write(response.content)
                audio_path = audio_file.name
            
            print("DEBUG: Transcribing with Whisper API")
            # Use OpenAI's Whisper API
            with open(audio_path, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
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