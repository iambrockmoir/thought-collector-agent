from flask import Flask, request
import logging
import sys
import os
from openai import OpenAI
from supabase import create_client
from pinecone import Pinecone
from datetime import datetime

from .services.audio import AudioService
from .services.chat import ChatService
from .services.sms import SMSService
from .services.storage import StorageService
from .services.vector import VectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

# Get environment variables
openai_key = os.getenv('OPENAI_API_KEY')
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
audio_converter_url = os.getenv('AUDIO_CONVERTER_URL')

# Initialize OpenAI client
try:
    openai_client = OpenAI(api_key=openai_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}", exc_info=True)
    openai_client = None

# Initialize Supabase client
try:
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}", exc_info=True)
    supabase = None

# Initialize Pinecone
try:
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index_name = os.getenv('PINECONE_INDEX', 'thoughts-index')
    index = pc.Index(index_name)
    logger.info("Successfully initialized Pinecone index")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    index = None

# Initialize vector service
vector_service = VectorService(index)

# Initialize services
storage_service = StorageService(supabase)
audio_service = AudioService(openai_client, audio_converter_url)
chat_service = ChatService(
    openai_client=openai_client,
    storage_service=storage_service,
    vector_service=vector_service
)
sms_service = SMSService(
    twilio_auth=(twilio_account_sid, twilio_auth_token),
    audio_service=audio_service,
    chat_service=chat_service,
    storage_service=storage_service
)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming messages"""
    try:
        # Get message details
        from_number = request.values.get('From', '')
        content_type = request.values.get('MediaContentType0', '')
        media_url = request.values.get('MediaUrl0', '')
        body = request.values.get('Body', '').strip()
        
        logger.info(f"Received message from {from_number}")
        logger.info(f"Content type: {content_type}")
        logger.info(f"Message body: {body}")

        # Let SMS service handle the message
        return sms_service.handle_incoming_message(
            from_number=from_number,
            body=body,
            media_url=media_url,
            content_type=content_type
        )
            
    except Exception as e:
        logger.error(f"Failed to process message: {str(e)}", exc_info=True)
        return '', 200  # Silent fail