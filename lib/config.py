from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    # OpenAI settings
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    
    # Twilio settings
    twilio_account_sid: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    twilio_auth_token: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    twilio_phone_number: str = os.getenv('TWILIO_PHONE_NUMBER', '')
    
    # Supabase settings
    supabase_url: str = os.getenv('SUPABASE_URL', '')
    supabase_key: str = os.getenv('SUPABASE_KEY', '')
    
    # Pinecone settings
    pinecone_api_key: str = os.getenv('PINECONE_API_KEY', '')
    pinecone_environment: str = os.getenv('PINECONE_ENVIRONMENT', '')

def get_settings() -> Settings:
    return Settings()