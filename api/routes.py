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
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from supabase.lib.client_options import ClientOptions

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
try:
    options = ClientOptions(
        schema='public',
        headers={},
        auto_refresh_token=True,
        persist_session=True,
        auto_refresh_token_timer=30
    )
    
    supabase_client = create_client(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        options=options
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {str(e)}")
    raise

logger.info("Initializing Twilio client...")
twilio_client = Client(
    settings.twilio_account_sid,
    settings.twilio_auth_token
)
logger.info("Twilio client initialized successfully")

# Initialize Pinecone
logger.info("Starting application initialization...")

try:
    logger.info(f"Initializing Pinecone with API key: {settings.pinecone_api_key[:8]}...")
    logger.info(f"Index name: {settings.pinecone_index}")
    logger.info(f"Host: {settings.pinecone_host}")
    
    vector_service = VectorService(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index,
        host=settings.pinecone_host
    )
    logger.info("Pinecone initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    logger.error(f"Error type: {type(e)}")
    logger.error(f"Error args: {e.args}")
    vector_service = None

# Initialize services
logger.info("Initializing services...")
try:
    if vector_service is None:
        logger.warning("Initializing storage service without vector service")
    else:
        logger.info("Initializing storage service with vector service")
    
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

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Increase the timeout for the whole request
        request.app.state.timeout = 60  # seconds
        
        # Rest of the handler code...
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return PlainTextResponse(
            "I apologize, but I encountered an error. Please try again.",
            status_code=200  # Return 200 so Twilio doesn't retry
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