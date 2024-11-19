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
import pinecone
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
pinecone.init(
    api_key=os.getenv('PINECONE_API_KEY'),
    environment=os.getenv('PINECONE_ENVIRONMENT')
)
index = pinecone.Index(os.getenv('PINECONE_INDEX'))

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

def process_chat_message(message, from_number=None):
    """Process a chat message using OpenAI"""
    try:
        if not client:
            logger.error("OpenAI client not initialized")
            return "Sorry, I'm having trouble connecting to my brain right now."
            
        logger.info(f"Processing chat message: {message}")
        
        # Store user's message
        if from_number:
            store_chat_message(from_number, message, is_user=True)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who responds in a friendly, conversational way."},
                {"role": "user", "content": message}
            ],
            max_tokens=150
        )
        reply = response.choices[0].message.content
        logger.info(f"Generated reply: {reply}")
        
        # Store assistant's response
        if from_number:
            store_chat_message(from_number, reply, is_user=False)
            
        return reply
    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}", exc_info=True)
        return f"I'm having trouble processing your message right now. Error: {str(e)}"

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
def legacy_webhook():
    """Handle legacy webhook endpoint"""
    return handle_sms()

@app.route('/api/sms', methods=['POST'])
def handle_sms():
    """Handle incoming SMS messages"""
    try:
        form_data = request.form.to_dict()
        from_number = form_data.get('From', '')
        media_url = form_data.get('MediaUrl0', '')
        
        if media_url:
            logger.info(f"Received audio from {from_number}: {media_url}")
            
            # Download from Twilio
            auth = (twilio_account_sid, twilio_auth_token)
            audio_response = requests.get(media_url, auth=auth)
            
            if audio_response.status_code != 200:
                logger.error(f"Twilio download failed: {audio_response.status_code}")
                send_twilio_message(from_number, "Sorry, I couldn't download your audio.")
                return
            
            logger.info("Successfully downloaded from Twilio")
            
            # Process audio through converter service...
            # (existing audio conversion code)
            
            # Transcribe
            logger.info("Starting transcription...")
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
                metadata={
                    'source': 'twilio',
                    'content_type': audio_response.headers.get('Content-Type')
                }
            )
            
            # Process transcribed text
            logger.info("Processing transcribed text with ChatGPT...")
            response = process_chat_message(transcribed_text, from_number)
            logger.info(f"ChatGPT response: {response}")
            
            # Update chat message with related thought
            if thought_id:
                # Get the last two chat messages (user's transcribed message and AI's response)
                recent_chats = supabase.table('chat_history')\
                    .select('id')\
                    .eq('user_phone', from_number)\
                    .order('created_at', desc=True)\
                    .limit(2)\
                    .execute()
                    
                for chat in recent_chats.data:
                    supabase.table('chat_history')\
                        .update({'related_thoughts': [thought_id]})\
                        .eq('id', chat['id'])\
                        .execute()
            
            # Send final response
            logger.info(f"Sending response to {from_number}")
            send_twilio_message(from_number, f"I heard: '{transcribed_text}'\n\nMy response: {response}")
            logger.info("Response sent successfully")
            
        else:
            # Handle text messages as before
            reply = process_chat_message(message_body, from_number)
            resp = MessagingResponse()
            resp.message(reply)
            return str(resp), 200, {'Content-Type': 'text/xml'}
            
    except Exception as e:
        logger.error(f"SMS handling failed: {str(e)}", exc_info=True)
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again.")
        return str(resp), 200, {'Content-Type': 'text/xml'}

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
    """Process audio message in the background and send response when done"""
    try:
        logger.info(f"=== Starting Async Audio Processing for {from_number} ===")
        logger.info(f"Media URL: {media_url}")
        
        # Download from Twilio
        auth = (twilio_account_sid, twilio_auth_token)
        logger.info("Downloading from Twilio...")
        audio_response = requests.get(media_url, auth=auth, timeout=10)
        
        if audio_response.status_code != 200:
            logger.error(f"Twilio download failed: {audio_response.status_code}")
            send_twilio_message(from_number, "Sorry, I couldn't download your audio.")
            return
            
        logger.info("Successfully downloaded from Twilio")
        
        # Process audio through converter service...
        # (existing audio conversion code)
        
        # Transcribe
        logger.info("Starting transcription...")
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
            metadata={
                'source': 'twilio',
                'content_type': audio_response.headers.get('Content-Type')
            }
        )
        
        # Process transcribed text
        logger.info("Processing transcribed text with ChatGPT...")
        response = process_chat_message(transcribed_text, from_number)
        logger.info(f"ChatGPT response: {response}")
        
        # Update chat message with related thought
        if thought_id:
            # Get the last two chat messages (user's transcribed message and AI's response)
            recent_chats = supabase.table('chat_history')\
                .select('id')\
                .eq('user_phone', from_number)\
                .order('created_at', desc=True)\
                .limit(2)\
                .execute()
                
            for chat in recent_chats.data:
                supabase.table('chat_history')\
                    .update({'related_thoughts': [thought_id]})\
                    .eq('id', chat['id'])\
                    .execute()
        
        # Send final response
        logger.info(f"Sending response to {from_number}")
        send_twilio_message(from_number, f"I heard: '{transcribed_text}'\n\nMy response: {response}")
        logger.info("Response sent successfully")
        
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