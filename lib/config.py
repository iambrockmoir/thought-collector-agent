from pydantic import BaseModel
from dotenv import load_dotenv
import os
import base64

load_dotenv()

class Settings(BaseModel):
    # OpenAI settings
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    
    # Twilio settings
    twilio_account_sid: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    twilio_auth_token: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    twilio_phone_number: str = os.getenv('TWILIO_PHONE_NUMBER', '')
    
    @property
    def twilio_auth(self) -> str:
        auth_string = f"{self.twilio_account_sid}:{self.twilio_auth_token}"
        return base64.b64encode(auth_string.encode()).decode()
    
    # Supabase settings
    supabase_url: str = os.getenv('SUPABASE_URL', '')
    supabase_key: str = os.getenv('SUPABASE_KEY', '')
    
    # Pinecone settings
    pinecone_api_key: str = os.getenv('PINECONE_API_KEY', '')
    pinecone_environment: str = os.getenv('PINECONE_ENVIRONMENT', '')
    
    # Audio converter settings
    audio_converter_url: str = os.getenv('AUDIO_CONVERTER_URL', 
        'https://your-rails-app.railway.app/convert')

def get_settings() -> Settings:
    return Settings()