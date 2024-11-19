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

def process_audio_message(media_url):
    """Process an audio message"""
    try:
        logger.info("=== Starting Audio Processing ===")
        logger.info(f"Processing audio from URL: {media_url}")
        
        # Download the audio file from Twilio with authentication
        auth = (twilio_account_sid, twilio_auth_token)
        logger.info("Attempting to download from Twilio")
        audio_response = requests.get(media_url, auth=auth)
        
        logger.info(f"Twilio download status: {audio_response.status_code}")
        if audio_response.status_code != 200:
            logger.error(f"Failed to download audio from Twilio: {audio_response.status_code}")
            logger.error(f"Response content: {audio_response.text}")
            return "Sorry, I had trouble downloading your audio message."
            
        # Save the audio file temporarily
        logger.info("Saving audio file")
        with open("/tmp/original_audio.amr", "wb") as f:
            f.write(audio_response.content)
            
        logger.info("Successfully saved audio file")
        
        # Send to converter service
        converter_url = f"{audio_converter_url}/convert"
        logger.info(f"Sending to converter service: {converter_url}")
        
        with open("/tmp/original_audio.amr", "rb") as audio_file:
            files = {
                'audio': ('audio.amr', audio_file, 'audio/amr')
            }
            logger.info("Attempting converter service request")
            converter_response = requests.post(
                converter_url,
                files=files
            )
        
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
            
        # Transcribe the audio
        logger.info("Starting transcribe")
        with open("/tmp/audio.mp3", "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        
        transcribed_text = transcript.text
        logger.info(f"Transcribed text: {transcribed_text}")
        
        # Process the transcribed text
        return process_chat_message(transcribed_text)
        
    except Exception as e:
        logger.error("=== Error in Audio Processing ===")
        logger.error(f"Audio processing failed: {str(e)}", exc_info=True)
        return f"Sorry, I had trouble processing your audio message. Error: {str(e)}"

def process_chat_message(message):
    """Process a chat message using OpenAI"""
    try:
        if not client:
            logger.error("OpenAI client not initialized")
            return "Sorry, I'm having trouble connecting to my brain right now."
            
        logger.info(f"Processing chat message: {message}")
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

@app.route('/webhook', methods=['POST'])
def legacy_webhook():
    """Handle legacy webhook endpoint"""
    logger.info("Received request to legacy webhook")
    return handle_sms()

@app.route('/api/sms', methods=['POST'])
def handle_sms():
    """Handle incoming SMS messages"""
    try:
        logger.info("=== Starting SMS Handler ===")
        form_data = request.form.to_dict()
        logger.info(f"Received SMS webhook with data: {form_data}")
        
        message_body = form_data.get('Body', '')
        from_number = form_data.get('From', '')
        
        # Log all media-related fields
        for key in form_data.keys():
            if 'Media' in key:
                logger.info(f"Media field found: {key}: {form_data[key]}")
        
        media_url = form_data.get('MediaUrl0', '')
        media_type = form_data.get('MediaContentType0', '')
        
        logger.info(f"From: {from_number}")
        logger.info(f"Body: {message_body}")
        logger.info(f"Media URL: {media_url}")
        logger.info(f"Media Type: {media_type}")
        
        if media_url:
            logger.info("Processing as media message")
            reply = process_audio_message(media_url)
            logger.info(f"Media processing reply: {reply}")
        else:
            logger.info("Processing as text message")
            reply = process_chat_message(message_body)
            logger.info(f"Text processing reply: {reply}")
        
        logger.info("Creating TwiML response")
        resp = MessagingResponse()
        resp.message(reply)
        
        response_text = str(resp)
        logger.info(f"Sending response: {response_text}")
        logger.info("=== Finishing SMS Handler ===")
        
        return response_text, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error("=== Error in SMS Handler ===")
        logger.error(f"SMS processing failed: {str(e)}", exc_info=True)
        return f"Sorry, I had trouble processing your SMS message. Error: {str(e)}"

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

# For local development
if __name__ == '__main__':
    app.run(debug=True)