from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Request WAV format directly
            wav_url = media_url + ".wav"
            print(f"DEBUG: Downloading WAV from: {wav_url}")
            
            response = requests.get(
                wav_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                headers={'Accept': 'audio/wav'}
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                print(f"ERROR: Response content: {response.content[:200]}")  # First 200 bytes
                raise Exception(f"Failed to download audio: {response.status_code}")
            
            # Save the WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                audio_file.write(response.content)
                audio_path = audio_file.name
                print(f"DEBUG: Saved WAV file to: {audio_path}")
            
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