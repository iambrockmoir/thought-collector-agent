from typing import Dict, Any
import requests
import openai
from lib.config import get_settings
import tempfile
import os
from amr_utils.amr_readers import AMR_Reader
import wave
import numpy as np
from io import BytesIO

settings = get_settings()
openai.api_key = settings.openai_api_key

class AudioProcessor:
    async def process_audio_message(self, media_url: str, user_phone: str) -> Dict[str, Any]:
        try:
            print(f"DEBUG: Processing media URL: {media_url}")
            
            # Download AMR file
            response = requests.get(
                media_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            
            if response.status_code != 200:
                print(f"ERROR: Failed to download audio: {response.status_code}")
                raise Exception(f"Failed to download audio: {response.status_code}")
            
            # Save AMR file
            with tempfile.NamedTemporaryFile(suffix='.amr', delete=False) as amr_file:
                amr_file.write(response.content)
                amr_path = amr_file.name
                print(f"DEBUG: Saved AMR file: {amr_path}")
            
            # Read AMR file
            reader = AMR_Reader()
            amr_data = reader.load(amr_path)
            print(f"DEBUG: Loaded AMR data, length: {len(amr_data)}")
            
            # Convert to WAV
            wav_path = amr_path.replace('.amr', '.wav')
            with wave.open(wav_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample
                wav_file.setframerate(8000)  # AMR standard sample rate
                wav_file.writeframes(np.array(amr_data, dtype=np.int16).tobytes())
            
            print(f"DEBUG: Converted to WAV: {wav_path}")
            
            # First convert AMR to MP3 if needed
            if 'audio/amr' in response.headers.get('Content-Type', ''):
                print("DEBUG: Converting AMR to MP3...")
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
                
                response.content = converter_response.content
                response.headers['Content-Type'] = 'audio/mp3'
                print(f"DEBUG: Conversion successful, got {len(response.content)} bytes of MP3")
            
            # Create a temporary file with the correct extension
            extension = 'mp3' if 'audio/mp3' in response.headers.get('Content-Type', '') else 'amr'
            temp_filename = f'temp_audio.{extension}'
            
            # Save the audio data to a temporary file
            with open(temp_filename, 'wb') as f:
                f.write(response.content)
            
            print("DEBUG: Transcribing with Whisper API")
            # Open the file and send to Whisper API
            with open(temp_filename, 'rb') as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            # Clean up the temporary file
            os.remove(temp_filename)
            
            print(f"DEBUG: Transcription result: {transcript}")
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