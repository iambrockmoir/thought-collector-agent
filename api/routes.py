from flask import Flask, request
import logging
import sys
import os
from openai import OpenAI
from supabase import create_client
from pinecone import Pinecone
from datetime import datetime
import asyncio
from functools import partial
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

# Initialize services with proper order and logging
try:
    logger.info("Initializing Pinecone...")
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index_name = os.getenv('PINECONE_INDEX', 'thoughts-index')
    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    logger.info(f"Pinecone initialized. Index stats: {stats}")
    vector_service = VectorService(index)
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}", exc_info=True)
    vector_service = None
    
try:
    logger.info("Initializing services...")
    storage_service = StorageService(supabase, vector_service)
    audio_service = AudioService(openai_client, audio_converter_url)
    chat_service = ChatService(
        openai_client=openai_client,
        storage_service=storage_service,
        vector_service=vector_service
    )
    logger.info("All services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
    raise

sms_service = SMSService(
    twilio_auth=(twilio_account_sid, twilio_auth_token),
    audio_service=audio_service,
    chat_service=chat_service,
    storage_service=storage_service
)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Twilio webhook"""
    try:
        # Get message details
        from_number = request.form.get('From')
        body = request.form.get('Body', '')
        num_media = int(request.form.get('NumMedia', 0))
        
        logger.info(f"Received message from {from_number}")
        
        # Handle media messages
        if num_media > 0:
            content_type = request.form.get('MediaContentType0', '')
            media_url = request.form.get('MediaUrl0', '')
            logger.info(f"Content type: {content_type}")
            logger.info(f"Message body: {body}")
            
            # Handle audio messages
            if 'audio' in content_type:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(
                        sms_service.handle_incoming_message(
                            from_number=from_number,
                            body=body,
                            media_url=media_url,
                            content_type=content_type
                        )
                    )
                finally:
                    loop.close()
                return str(response)
        
        # Handle text messages synchronously
        logger.info(f"Processing text message: {body[:50]}...")
        return str(sms_service.handle_text_message(from_number, body))
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return str(
            MessagingResponse().message(
                "Sorry, I encountered an error. Please try again."
            )
        )

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