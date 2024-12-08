import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI settings
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    
    # Twilio settings
    twilio_account_sid: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    twilio_auth_token: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    
    # Audio converter settings
    audio_converter_url: str = os.getenv('AUDIO_CONVERTER_URL', 'https://audio-converter-service.vercel.app')

def get_settings():
    return Settings() 