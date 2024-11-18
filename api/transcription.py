from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile
import os
from io import BytesIO
from lib.database import Database
from datetime import datetime

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Download audio from Twilio
            response = requests.get(
                media_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                raise Exception(f"Failed to download audio: {response.status_code}")
            
            # Send to Rails converter service
            print("DEBUG: Converting audio format...")
            files = {
                'audio': ('audio.amr', BytesIO(response.content), 'audio/amr')
            }
            
            converter_response = requests.post(
                'https://audio-converter-service-production.up.railway.app/convert',
                files=files
            )
            
            if converter_response.status_code != 200:
                print(f"DEBUG: Conversion failed with status {converter_response.status_code}")
                raise Exception(f"Conversion failed: {converter_response.text}")
            
            print(f"DEBUG: Conversion successful, got {len(converter_response.content)} bytes of MP3")
            
            # Create temporary file for Whisper API
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(converter_response.content)
                temp_path = temp_file.name
                
                print("DEBUG: Transcribing with Whisper API")
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=open(temp_path, 'rb'),
                    response_format="text"
                )
                
                # Clean up temp file
                os.remove(temp_path)
            
            print(f"DEBUG: Transcription result: {transcript}")
            
            # Store in database
            try:
                db = Database()
                thought_data = {
                    'user_phone': user_phone,
                    'audio_url': media_url,
                    'transcription': transcript,
                    'metadata': {
                        'source': 'sms',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
                await db.store_thought(thought_data)
                print("DEBUG: Thought stored in database")
            except Exception as db_error:
                print(f"WARNING: Database storage failed: {str(db_error)}")
                # Continue even if storage fails - we can still return the transcription
            
            return {
                "transcription": transcript,
                "message": f"I heard: {transcript}"
            }
            
        except Exception as e:
            print(f"Error processing audio: {str(e)}")
            import traceback
            print("Full error:", traceback.format_exc())
            return {
                "transcription": "",
                "message": "Sorry, I couldn't process that audio. Please try again."
            }