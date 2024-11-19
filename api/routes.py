from flask import Flask, jsonify, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import logging
import sys
import os
from openai import OpenAI
import requests
from urllib.parse import urlparse
import json
import time
from requests.exceptions import Timeout, RequestException
import threading
from supabase import create_client
from pinecone import Pinecone
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

# Initialize clients
openai_key = os.getenv('OPENAI_API_KEY')
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
audio_converter_url = os.getenv('AUDIO_CONVERTER_URL')

logger.info(f"OpenAI API Key available: {bool(openai_key)}")
logger.info(f"Twilio credentials available: {bool(twilio_account_sid and twilio_auth_token)}")
logger.info(f"Audio Converter URL available: {bool(audio_converter_url)}")

try:
    client = OpenAI(api_key=openai_key)
    twilio_client = Client(twilio_account_sid, twilio_auth_token)
    logger.info("OpenAI and Twilio clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize clients: {str(e)}", exc_info=True)
    client = None
    twilio_client = None

# Initialize clients
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Get the index name from environment variable with fallback
index_name = os.getenv('PINECONE_INDEX', 'thoughts-index')

# Add debug logging
logger.info(f"Initializing Pinecone index: {index_name}")
try:
    # Get index using new API
    index = pc.Index(index_name)
    logger.info("Successfully initialized Pinecone index")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    raise

def process_audio_message(media_url):
    """Process an audio message"""
    try:
        start_time = time.time()
        logger.info("=== Starting Audio Processing ===")
        logger.info(f"Processing audio from URL: {media_url}")
        
        # Download the audio file from Twilio with authentication
        auth = (twilio_account_sid, twilio_auth_token)
        logger.info("Attempting to download from Twilio")
        try:
            audio_response = requests.get(media_url, auth=auth, timeout=10)  # 10 second timeout
            logger.info(f"Twilio download took {time.time() - start_time:.2f} seconds")
        except Timeout:
            logger.error("Timeout downloading from Twilio")
            return "Sorry, the download took too long. Please try again."
        except RequestException as e:
            logger.error(f"Error downloading from Twilio: {str(e)}")
            return "Sorry, there was a problem downloading your audio."
        
        logger.info(f"Twilio download status: {audio_response.status_code}")
        logger.info(f"Twilio content type: {audio_response.headers.get('Content-Type')}")
        
        if audio_response.status_code != 200:
            logger.error(f"Failed to download audio from Twilio: {audio_response.status_code}")
            logger.error(f"Response content: {audio_response.text}")
            return "Sorry, I had trouble downloading your audio message."
            
        # Save the audio file temporarily
        logger.info("Saving audio file")
        with open("/tmp/original_audio.amr", "wb") as f:
            f.write(audio_response.content)
            
        logger.info("Successfully saved audio file")
        file_size = len(audio_response.content)
        logger.info(f"Audio file size: {file_size} bytes")
        
        # Send to converter service
        logger.info(f"Sending to converter service: {audio_converter_url}")
        
        with open("/tmp/original_audio.amr", "rb") as audio_file:
            files = {
                'audio': ('audio.amr', audio_file, audio_response.headers.get('Content-Type', 'audio/amr'))
            }
            logger.info(f"Sending file with content type: {files['audio'][2]}")
            
            try:
                converter_start = time.time()
                converter_response = requests.post(
                    audio_converter_url,
                    files=files,
                    timeout=30  # 30 second timeout
                )
                logger.info(f"Converter request took {time.time() - converter_start:.2f} seconds")
            except Timeout:
                logger.error("Timeout from converter service")
                return "Sorry, the conversion took too long. Please try again."
            except RequestException as e:
                logger.error(f"Error from converter service: {str(e)}")
                return "Sorry, there was a problem converting your audio."
        
        logger.info(f"Converter response status: {converter_response.status_code}")
        
        if converter_response.status_code != 200:
            logger.error(f"Converter error status: {converter_response.status_code}")
            logger.error(f"Converter error content: {converter_response.text}")
            return "Sorry, I had trouble processing your audio message."
            
        # Save the converted audio
        logger.info("Saving converted audio")
        with open("/tmp/audio.mp3", "wb") as f:
            f.write(converter_response.content)
            
        logger.info("Successfully saved converted audio")
        converted_size = len(converter_response.content)
        logger.info(f"Converted file size: {converted_size} bytes")
            
        # Transcribe the audio
        logger.info("Starting transcription")
        transcribe_start = time.time()
        with open("/tmp/audio.mp3", "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        logger.info(f"Transcription took {time.time() - transcribe_start:.2f} seconds")
        
        transcribed_text = transcript.text
        logger.info(f"Transcribed text: {transcribed_text}")
        
        total_time = time.time() - start_time
        logger.info(f"Total processing time: {total_time:.2f} seconds")
        
        # Process the transcribed text
        return process_chat_message(transcribed_text)
        
    except Exception as e:
        logger.error("=== Error in Audio Processing ===")
        logger.error(f"Audio processing failed: {str(e)}", exc_info=True)
        return f"Sorry, I had trouble processing your audio message. Error: {str(e)}"

def store_chat_message(phone_number, message, is_user=True, related_thoughts=None):
    """Store a message in chat_history"""
    try:
        chat_data = {
            'user_phone': phone_number,
            'message': message,
            'is_user': is_user,
            'related_thoughts': related_thoughts
        }
        
        result = supabase.table('chat_history').insert(chat_data).execute()
        chat_id = result.data[0]['id']
        logger.info(f"Stored chat message with ID: {chat_id}")
        return chat_id
        
    except Exception as e:
        logger.error(f"Failed to store chat message: {str(e)}", exc_info=True)
        return None

def store_thought(phone_number, audio_url, transcription=None):
    """Store a thought from audio"""
    try:
        thought_data = {
            'user_phone': phone_number,
            'audio_url': audio_url,
            'transcription': transcription,  # This will be None initially
            'metadata': {'status': 'received'}
        }
        
        result = supabase.table('thoughts').insert(thought_data).execute()
        thought_id = result.data[0]['id']
        logger.info(f"Stored thought with ID: {thought_id}")
        return thought_id
        
    except Exception as e:
        logger.error(f"Failed to store thought: {str(e)}", exc_info=True)
        return None

def process_chat_message(message, from_number):
    """Process a text message using ChatGPT"""
    try:
        logger.info(f"Processing chat message: {message[:50]}...")  # Log first 50 chars
        
        # Simple message array without history
        messages = [
            {"role": "system", "content": "You are a helpful assistant who helps people organize and reflect on their thoughts."},
            {"role": "user", "content": message}
        ]
        
        # Get response from ChatGPT
        logger.info("Sending to ChatGPT...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content
        logger.info(f"ChatGPT response: {ai_response[:50]}...")  # Log first 50 chars
        
        # Store messages in chat history
        store_chat_message(from_number, message, True)  # User message
        store_chat_message(from_number, ai_response, False)  # AI response
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Failed to process chat message: {str(e)}", exc_info=True)
        return "Sorry, I had trouble processing your message. Please try again."

def get_chat_history(phone_number, limit=5):
    """Get recent chat history for a user"""
    try:
        response = supabase.table('chat_history')\
            .select('*')\
            .eq('user_phone', phone_number)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
            
        # Reverse to get chronological order
        return list(reversed(response.data))
    except Exception as e:
        logger.error(f"Failed to get chat history: {str(e)}")
        return []

def store_chat_message(phone_number, content, is_user):
    """Store a chat message in the database"""
    try:
        data = {
            'user_phone': phone_number,
            'content': content,
            'is_user': is_user,
            'created_at': datetime.utcnow().isoformat()
        }
        
        response = supabase.table('chat_history').insert(data).execute()
        logger.info(f"Stored chat message for {phone_number}")
        return response.data[0]['id'] if response.data else None
        
    except Exception as e:
        logger.error(f"Failed to store chat message: {str(e)}")
        return None

@app.route('/')
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            "status": "healthy",
            "message": "ThoughtCollector API is running",
            "version": "1.0.0"
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def store_processing_status(phone_number, media_url, status='pending'):
    """Store the processing status in Supabase"""
    try:
        status_data = {
            'user_phone': phone_number,
            'media_url': media_url,
            'status': status,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('processing_queue').insert(status_data).execute()
        return result.data[0]['id']
    except Exception as e:
        logger.error(f"Failed to store processing status: {str(e)}")
        return None

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

        # Handle audio messages
        if content_type and media_url:
            logger.info("Processing audio message")
            # Process directly instead of async
            try:
                # Download from Twilio
                auth = (twilio_account_sid, twilio_auth_token)
                logger.info("Downloading from Twilio...")
                audio_response = requests.get(media_url, auth=auth, timeout=30)
                
                if audio_response.status_code != 200:
                    logger.error(f"Twilio download failed: {audio_response.status_code}")
                    resp = MessagingResponse()
                    resp.message("Sorry, I couldn't download your audio.")
                    return str(resp), 200, {'Content-Type': 'text/xml'}
                    
                # Save the audio file
                with open("/tmp/original_audio.amr", "wb") as f:
                    f.write(audio_response.content)
                    
                # Convert audio
                with open("/tmp/original_audio.amr", "rb") as audio_file:
                    files = {
                        'audio': ('audio.amr', audio_file, 'audio/amr')
                    }
                    converter_response = requests.post(
                        audio_converter_url,
                        files=files,
                        timeout=30
                    )
                    
                if converter_response.status_code != 200:
                    logger.error(f"Converter failed: {converter_response.status_code}")
                    resp = MessagingResponse()
                    resp.message("Sorry, I had trouble converting your audio.")
                    return str(resp), 200, {'Content-Type': 'text/xml'}
                    
                # Save converted audio
                with open("/tmp/audio.mp3", "wb") as f:
                    f.write(converter_response.content)
                
                # Transcribe
                with open("/tmp/audio.mp3", "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                
                transcribed_text = transcript.text
                logger.info(f"Transcription result: {transcribed_text}")
                
                # Store thought
                thought_id = store_thought(
                    phone_number=from_number,
                    audio_url=media_url,
                    transcription=transcribed_text,
                    metadata={'source': 'twilio'}
                )
                
                # Send success response
                resp = MessagingResponse()
                resp.message("Thought saved!")
                return str(resp), 200, {'Content-Type': 'text/xml'}
                
            except Exception as e:
                logger.error(f"Audio processing failed: {str(e)}", exc_info=True)
                resp = MessagingResponse()
                resp.message("Sorry, something went wrong processing your audio.")
                return str(resp), 200, {'Content-Type': 'text/xml'}
            
        # Handle text messages
        elif body:
            logger.info("Processing text message")
            response = process_chat_message(body, from_number)
            
            resp = MessagingResponse()
            resp.message(response)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        else:
            logger.warning("Received message with no content")
            return '', 200
            
    except Exception as e:
        logger.error(f"Failed to process message: {str(e)}", exc_info=True)
        return '', 200  # Silent fail

@app.route('/debug')
def debug_info():
    """Debug endpoint"""
    try:
        return jsonify({
            "python_version": sys.version,
            "endpoints": [
                {"path": "/", "methods": ["GET"]},
                {"path": "/debug", "methods": ["GET"]},
                {"path": "/api/sms", "methods": ["POST"]},
                {"path": "/webhook", "methods": ["POST"]}
            ]
        })
    except Exception as e:
        logger.error(f"Debug info failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

def process_audio_message_async(media_url, from_number):
    """Process audio message in the background"""
    try:
        logger.info(f"=== Starting Async Audio Processing for {from_number} ===")
        
        # Download from Twilio
        auth = (twilio_account_sid, twilio_auth_token)
        logger.info("Downloading from Twilio...")
        audio_response = requests.get(media_url, auth=auth, timeout=30)  # Increased timeout
        
        if audio_response.status_code != 200:
            logger.error(f"Twilio download failed: {audio_response.status_code}")
            send_twilio_message(from_number, "Sorry, I couldn't download your audio.")
            return
            
        # Save the audio file
        with open("/tmp/original_audio.amr", "wb") as f:
            f.write(audio_response.content)
            
        # Convert audio (using your existing converter service)
        with open("/tmp/original_audio.amr", "rb") as audio_file:
            files = {
                'audio': ('audio.amr', audio_file, 'audio/amr')
            }
            converter_response = requests.post(
                audio_converter_url,
                files=files,
                timeout=30
            )
            
        if converter_response.status_code != 200:
            logger.error(f"Converter failed: {converter_response.status_code}")
            send_twilio_message(from_number, "Sorry, I had trouble converting your audio.")
            return
            
        # Save converted audio
        with open("/tmp/audio.mp3", "wb") as f:
            f.write(converter_response.content)
        
        # Transcribe
        with open("/tmp/audio.mp3", "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        
        transcribed_text = transcript.text
        logger.info(f"Transcription result: {transcribed_text}")
        
        # Store thought
        thought_id = store_thought(
            phone_number=from_number,
            audio_url=media_url,
            transcription=transcribed_text,
            metadata={'source': 'twilio'}
        )
        
        # Send confirmation
        send_twilio_message(from_number, "Thought saved!")
        
    except Exception as e:
        logger.error(f"Async processing failed: {str(e)}", exc_info=True)
        send_twilio_message(from_number, "Sorry, something went wrong processing your audio.")

def send_twilio_message(to_number, message):
    """Send a message using Twilio"""
    try:
        logger.info(f"Sending message to {to_number}: {message[:50]}...")  # Log first 50 chars
        twilio_client.messages.create(
            body=message,
            to=to_number,
            from_=os.getenv('TWILIO_PHONE_NUMBER')
        )
        logger.info("Message sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Twilio message: {str(e)}")

# For local development
if __name__ == '__main__':
    app.run(debug=True)