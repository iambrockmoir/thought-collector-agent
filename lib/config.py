from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Twilio settings
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    test_phone_number: str  # Added this line for test phone number
    
    # OpenAI settings
    openai_api_key: str
    
    # Database settings
    supabase_url: str = ""  # Optional for now
    supabase_key: str = ""  # Optional for now
    
    # Pinecone settings
    pinecone_api_key: str = ""  # Optional for now
    pinecone_environment: str = ""  # Optional for now

    class Config:
        env_file = ".env"
        case_sensitive = False  # This makes it case-insensitive

@lru_cache()
def get_settings():
    return Settings()