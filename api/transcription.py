from typing import Dict, Any
import requests
import openai
import openamr
import wave
from lib.config import get_settings
import tempfile

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
            
            print("DEBUG: Converting AMR to PCM")
            # Convert AMR to PCM
            pcm_data = openamr.amr_decode(response.content)
            
            print("DEBUG: Creating WAV file")
            # Save as WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                with wave.open(wav_file.name, 'wb') as wav:
                    wav.setnchannels(1)  # Mono
                    wav.setsampwidth(2)  # 2 bytes per sample
                    wav.setframerate(8000)  # AMR standard sample rate
                    wav.writeframes(pcm_data)
                wav_path = wav_file.name
            
            print("DEBUG: Transcribing with Whisper API")
            # Use OpenAI's Whisper API
            with open(wav_path, "rb") as audio_file:
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