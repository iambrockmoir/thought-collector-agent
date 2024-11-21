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

from .services.audio import AudioService
from .services.chat import ChatService
from .services.sms import SMSService
from .services.storage import StorageService
from .services.vector import VectorService

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

# Get environment variables
openai_key = os.getenv('OPENAI_API_KEY')
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
audio_converter_url = os.getenv('AUDIO_CONVERTER_URL')

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_key)
logger.info("OpenAI client initialized successfully")

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)
logger.info("Supabase client initialized successfully")

# Initialize Pinecone and Vector Service
try:
    logger.info("Initializing Pinecone...")
    pc = pinecone.Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index(os.getenv('PINECONE_INDEX'))
    logger.info(f"Pinecone initialized. Index stats: {index.describe_index_stats()}")
    vector_service = VectorService(openai_client, index)
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}", exc_info=True)
    vector_service = None
    index = None

# Initialize other services
try:
    logger.info("Initializing services...")
    
    # Initialize base services first
    storage_service = StorageService(vector_service)
    audio_service = AudioService(openai_client)
    chat_service = ChatService(openai_client, storage_service)
    
    # Initialize SMS service last since it depends on the others
    sms_service = SMSService(
        chat_service=chat_service,
        audio_service=audio_service,
        storage_service=storage_service
    )
    
    logger.info("All services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise e

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming webhook from Twilio"""
    try:
        logger.info("Received webhook from Twilio")
        
        # Get message details
        from_number = request.values.get('From', '')
        body = request.values.get('Body', '')
        num_media = int(request.values.get('NumMedia', 0))
        
        logger.info(f"Received message from {from_number}")
        
        if num_media > 0:
            logger.info("Processing media message...")
            media_url = request.values.get('MediaUrl0')
            await sms_service.process_message(from_number, media_url=media_url)
        else:
            logger.info(f"Processing text message: {body}")
            await sms_service.process_message(from_number, body=body)
            
        logger.info("Successfully processed message")
        return 'OK'
        
    except Exception as e:
        logger.error(f"Failed to process webhook: {str(e)}")
        return str(e), 500

@app.route('/status', methods=['GET'])
def status():
    """Check service status"""
    try:
        status = {
            'pinecone': False,
            'vector_service': False,
            'stats': None
        }
        
        if index:
            try:
                stats = index.describe_index_stats()
                status['pinecone'] = True
                status['stats'] = stats
            except Exception as e:
                logger.error(f"Pinecone test failed: {str(e)}")
        
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
        if index:
            stats = index.describe_index_stats()
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