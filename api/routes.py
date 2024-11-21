from flask import Flask, request, Response
import logging
import sys
import os
from openai import OpenAI
from supabase import create_client
import pinecone
from datetime import datetime
import asyncio
from functools import partial, wraps
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from .services.audio import AudioService
from .services.chat import ChatService
from .services.sms import SMSService
from .services.storage import StorageService
from .services.vector import VectorService
from api import settings

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # Ensure our config takes precedence
)

# Create logger for this file
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

# Initialize clients
logger.info("Initializing OpenAI client...")
openai_client = OpenAI(api_key=settings.openai_api_key)
logger.info("OpenAI client initialized successfully")

logger.info("Initializing Supabase client...")
supabase_client = create_client(
    settings.supabase_url,
    settings.supabase_key
)
logger.info("Supabase client initialized successfully")

logger.info("Initializing Twilio client...")
twilio_client = Client(
    settings.twilio_account_sid,
    settings.twilio_auth_token
)
logger.info("Twilio client initialized successfully")

# Initialize Pinecone
logger.info("Initializing Pinecone...")
try:
    vector_service = VectorService(
        api_key=settings.pinecone_api_key,
        environment=settings.pinecone_environment,
        index_name=settings.pinecone_index,
        host=settings.pinecone_host
    )
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    vector_service = None

# Initialize services
logger.info("Initializing services...")
try:
    storage_service = StorageService(
        supabase_client=supabase_client,
        vector_service=vector_service
    )
    
    audio_service = AudioService(
        openai_client=openai_client,
        converter_url=settings.audio_converter_url
    )
    
    chat_service = ChatService(
        openai_client=openai_client,
        storage_service=storage_service
    )
    
    sms_service = SMSService(
        twilio_client=twilio_client,
        phone_number=settings.twilio_phone_number,
        audio_service=audio_service,
        storage_service=storage_service,
        chat_service=chat_service
    )
    
    logger.info("All services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise e

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming SMS webhook from Twilio"""
    try:
        logger.info("Received webhook from Twilio")
        
        # Extract message details
        from_number = request.form.get('From')
        message = request.form.get('Body', '')
        num_media = int(request.form.get('NumMedia', 0))
        
        logger.info(f"Received message from {from_number}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Handle media or text
        if num_media > 0:
            logger.info("Processing media message...")
            media_url = request.form.get('MediaUrl0')
            content_type = request.form.get('MediaContentType0')
            loop.run_until_complete(
                sms_service.handle_message(from_number, message, media_url, content_type)
            )
        else:
            logger.info(f"Processing text message: {message}")
            loop.run_until_complete(
                sms_service.handle_message(from_number, message)
            )
            
        logger.info("Successfully processed message")
        return 'OK', 200
        
    except Exception as e:
        logger.error(f"Failed to process webhook: {str(e)}")
        return 'Error', 500

@app.route('/status', methods=['GET'])
def status():
    """Check service status"""
    try:
        status = {
            'pinecone': False,
            'vector_service': False,
            'stats': None
        }
        
        if vector_service:
            status['vector_service'] = True
            
        return status, 200
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/', methods=['GET'])
def root():
    """Basic health check"""
    try:
        stats = None
        if vector_service:
            stats = vector_service.pinecone_index.describe_index_stats()
            # Convert stats to a serializable format
            stats = {
                'dimension': stats.get('dimension'),
                'index_fullness': stats.get('index_fullness'),
                'total_vector_count': stats.get('total_vector_count'),
                'namespaces': {
                    k: {'vector_count': v.get('vector_count')} 
                    for k, v in stats.get('namespaces', {}).items()
                }
            }
        
        return {
            'status': 'healthy',
            'pinecone_stats': stats if stats else None
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500