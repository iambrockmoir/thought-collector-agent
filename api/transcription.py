from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile
import os
from twilio.rest import Client

settings = get_settings()
openai.api_key = settings.openai_api_key
twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Extract message and media SIDs from URL
            parts = media_url.split('/')
            message_sid = parts[-3]
            media_sid = parts[-1]
            
            print(f"DEBUG: Message SID: {message_sid}, Media SID: {media_sid}")
            
            # Get media content using Twilio REST API
            media = twilio_client.messages(message_sid).media(media_sid).fetch()
            
            # Download the media content
            response = requests.get(
                media.uri,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                print(f"ERROR: Response headers: {response.headers}")
                raise Exception(f"Failed to download audio: {response.status_code}")
            
            # Save as MP3
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:
                audio_file.write(response.content)
                audio_path = audio_file.name
                print(f"DEBUG: Saved audio file to: {audio_path}")
                
                # Print file info
                file_size = os.path.getsize(audio_path)
                print(f"DEBUG: File size: {file_size} bytes")
                print(f"DEBUG: Content type from Twilio: {media.content_type}")
            
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