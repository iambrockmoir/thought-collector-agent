import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# OpenAI settings
openai_api_key = os.getenv('OPENAI_API_KEY')

# Supabase settings
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

# Twilio settings
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

# Pinecone settings
pinecone_api_key = os.getenv('PINECONE_API_KEY')
pinecone_environment = os.getenv('PINECONE_ENVIRONMENT')
pinecone_index = os.getenv('PINECONE_INDEX')
pinecone_host = os.getenv('PINECONE_HOST')

# Audio converter settings
audio_converter_url = os.getenv('AUDIO_CONVERTER_URL', 'https://audio-converter-service-production.up.railway.app/convert') 