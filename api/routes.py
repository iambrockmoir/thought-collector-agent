from flask import Flask, request, Response, jsonify
import logging
import sys
import os
from openai import OpenAI
from supabase import create_client, Client
import pinecone
from datetime import datetime
import asyncio
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import aiohttp

from .services.audio import AudioService
from .services.chat import ChatService
from .services.sms import SMSService
from .services.storage import StorageService
from .services.vector import VectorService
from . import settings

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
    supabase: Client = create_client(
        os.environ.get("SUPABASE_URL", ""),
        os.environ.get("SUPABASE_KEY", "")
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
        supabase_client=supabase,
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

def create_twiml_response(message: str) -> Response:
    """Create a TwiML response with the given message"""
    resp = MessagingResponse()
    resp.message(message)
    return Response(str(resp), mimetype='text/xml')

@app.route("/webhook", methods=['POST'])
async def webhook():
    try:
        logger.info("Webhook received")
        logger.info(f"Form data: {request.form.to_dict()}")
        
        form_data = request.form.to_dict()
        
        # Branch 1: Audio Message
        if request.form.get('MediaUrl0'):
            logger.info("Audio message detected")
            await forward_to_rails_processor(
                from_number=form_data.get('From'),
                media_url=request.form.get('MediaUrl0'),
                content_type=request.form.get('MediaContentType0')
            )
            logger.info("Audio forwarded to Rails")
            return Response(str(MessagingResponse()), mimetype='text/xml')
            
        # Branch 2: Text Message
        logger.info("Text message detected")
        response = await chat_service.process_message(
            user_phone=form_data.get('From'),
            message=form_data.get('Body')
        )
        logger.info(f"Generated response: {response}")
        
        # Store both the user message and response in chat history
        await storage_service.store_chat_message(
            message=form_data.get('Body'),
            from_number=form_data.get('From'),
            response=response
        )
        logger.info("Chat messages stored in database")
        
        # Create TwiML response
        twiml = MessagingResponse()
        twiml.message(response)
        return Response(str(twiml), mimetype='text/xml')

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        twiml = MessagingResponse()
        twiml.message(
            "I apologize, but I encountered an error. Please try again."
        )
        return Response(str(twiml), mimetype='text/xml')

async def forward_to_rails_processor(from_number: str, media_url: str, content_type: str):
    """Forward audio processing request to Rails"""
    async with aiohttp.ClientSession() as session:
        # Add Twilio authentication when downloading the audio file
        auth = aiohttp.BasicAuth(
            login=settings.twilio_account_sid,
            password=settings.twilio_auth_token
        )
        
        # Download audio with authentication
        async with session.get(media_url, auth=auth) as response:
            if response.status != 200:
                logger.error(f"Failed to download audio from Twilio: {await response.text()}")
                raise Exception("Failed to download audio from Twilio")
            
            audio_data = await response.read()
        
        # Prepare the file upload
        form_data = aiohttp.FormData()
        form_data.add_field('audio',
                          audio_data,
                          filename='audio.amr',
                          content_type=content_type)
        form_data.add_field('callback_url', f"https://{settings.vercel_url}/audio-callback")
        form_data.add_field('from_number', from_number)
        
        # Send to converter service using the Node.js endpoint
        async with session.post(
            f"{settings.audio_converter_url}/convert",
            data=form_data
        ) as response:
            if response.status != 200:
                logger.error(f"Failed to forward to Rails: {await response.text()}")
                raise Exception("Failed to forward audio processing")

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

@app.route("/audio-callback", methods=['POST'])
async def audio_callback():
    logger.info("Received request to /audio-callback")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request data: {request.get_data(as_text=True)}")
    
    try:
        data = request.json
        logger.info(f"Parsed JSON data: {data}")
        
        if not data.get('transcription'):
            logger.error("Missing transcription in request data")
            return jsonify({'status': 'error', 'message': 'Missing transcription'}), 400
            
        if not data.get('from_number'):
            logger.error("Missing from_number in request data")
            return jsonify({'status': 'error', 'message': 'Missing from_number'}), 400
        
        # Store in Supabase
        logger.info(f"Storing thought in Supabase for user: {data['from_number']}")
        thought_record = storage_service.store_thought(
            data['from_number'],
            data['transcription']
        )
        logger.info(f"Successfully stored thought record: {thought_record}")
        
        # Store embedding in Pinecone
        if vector_service:
            logger.info("Storing embedding in Pinecone")
            metadata = {
                'user_phone': data['from_number'],
                'thought_id': thought_record['id'],
                'created_at': thought_record['created_at']
            }
            logger.info(f"Embedding metadata: {metadata}")
            vector_service.store_embedding(
                data['transcription'],
                metadata=metadata
            )
            logger.info("Successfully stored embedding in Pinecone")
        else:
            logger.warning("Vector service not available - skipping embedding storage")
        
        # Generate and send response
        logger.info("Generating chat response")
        response = await chat_service.process_message(
            user_phone=data['from_number'],
            message=data['transcription']
        )
        logger.info(f"Generated chat response: {response}")
        
        logger.info(f"Sending SMS response to {data['from_number']}")
        await sms_service.send_message(data['from_number'], response)
        logger.info("Successfully sent SMS response")
        
        logger.info("Audio callback processing completed successfully")
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error in audio callback: {str(e)}")
        logger.error(f"Stack trace: {e.__traceback__}")
        logger.error(f"Request data that caused error: {request.get_data(as_text=True)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
