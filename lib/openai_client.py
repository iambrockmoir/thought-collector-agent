from openai import OpenAI
from typing import Optional
from lib.config import get_settings
from lib.error_handler import AppError

settings = get_settings()

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio file using OpenAI Whisper API
        """
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript

        except Exception as e:
            raise AppError(f"Transcription failed: {str(e)}", status_code=500)

    async def generate_response(self, query: str, context: Optional[str] = None) -> str:
        """
        Generate response using OpenAI ChatGPT API
        """
        try:
            messages = []
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Context from previous thoughts: {context}"
                })
            
            messages.append({
                "role": "user",
                "content": query
            })

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=150
            )

            # Extract the response text
            return response.choices[0].message.content

        except Exception as e:
            raise AppError(f"Response generation failed: {str(e)}", status_code=500)