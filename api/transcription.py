from typing import Dict, Any
import requests
import openai
import wave
import audioop
from lib.config import get_settings
import tempfile
import os

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Download AMR data
            response = requests.get(
                media_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                raise Exception(f"Failed to download audio: {response.status_code}")
            
            print(f"DEBUG: Downloaded audio size: {len(response.content)} bytes")
            print(f"DEBUG: Content type: {response.headers.get('Content-Type')}")
            
            # Save original AMR file for debugging
            with tempfile.NamedTemporaryFile(suffix='.amr', delete=False) as amr_file:
                amr_file.write(response.content)
                print(f"DEBUG: Saved original AMR to: {amr_file.name}")
            
            print("DEBUG: Converting audio")
            # Try direct conversion to WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                with wave.open(wav_file.name, 'wb') as wav:
                    wav.setnchannels(1)  # Mono
                    wav.setsampwidth(2)  # 2 bytes per sample
                    wav.setframerate(8000)  # AMR standard rate
                    wav.writeframes(response.content)
                wav_path = wav_file.name
                
                print(f"DEBUG: WAV file size: {os.path.getsize(wav_path)} bytes")
            
            print("DEBUG: Transcribing with Whisper API")
            # Use OpenAI's Whisper API
            with open(wav_path, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            print(f"DEBUG: Transcription result: '{transcript}'")
            
            if not transcript.strip():
                return {
                    "transcription": "",
                    "message": "I couldn't understand that audio. Please try speaking clearly and close to the microphone."
                }
            
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
                "message": "Sorry, I couldn't process that audio. Please try again. For best results, please record in a quiet environment and speak clearly."
            }