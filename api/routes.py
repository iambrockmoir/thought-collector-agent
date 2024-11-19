from flask import Flask, jsonify, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
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

# Check OpenAI configuration
openai_key = os.getenv('OPENAI_API_KEY')
logger.info(f"OpenAI API Key available: {bool(openai_key)}")
audio_converter_url = os.getenv('AUDIO_CONVERTER_URL')
logger.info(f"Audio Converter URL available: {bool(audio_converter_url)}")

try:
    client = OpenAI(api_key=openai_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}", exc_info=True)
    client = None

def process_audio_message(media_url):
    """Process an audio message"""
    try:
        logger.info(f"Processing audio from URL: {media_url}")
        
        # Download the audio file from Twilio
        audio_response = requests.get(media_url)
        if audio_response.status_code != 200:
            logger.error(f"Failed to download audio from Twilio: {audio_response.status_code}")
            return "Sorry, I had trouble downloading your audio message."
            
        # Save the audio file temporarily
        with open("/tmp/original_audio.mp3", "wb") as f:
            f.write(audio_response.content)
            
        logger.info("Downloaded audio file from Twilio")
        
        # Send the file to the converter service
        files = {
            'file': ('audio.mp3', open('/tmp/original_audio.mp3', 'rb'), 'audio/mpeg')
        }
        
        logger.info(f"Sending to converter service: {audio_converter_url}")
        converter_response = requests.post(
            audio_converter_url,
            files=files
        )
        
        logger.info(f"Converter response status: {converter_response.status_code}")
        logger.info(f"Converter response: {converter_response.text}")
        
        if converter_response.status_code != 200:
            logger.error(f"Converter error: {converter_response.text}")
            return "Sorry, I had trouble processing your audio message."
            
        converted_url = converter_response.json().get("url")
        if not converted_url:
            logger.error("No converted URL received")
            return "Sorry, I couldn't convert your audio message."
            
        logger.info(f"Audio converted successfully: {converted_url}")
        
        # Download the converted audio
        converted_audio = requests.get(converted_url)
        with open("/tmp/audio.mp3", "wb") as f:
            f.write(converted_audio.content)
            
        # Transcribe the audio
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
        form_data = request.form.to_dict()
        logger.info(f"Received SMS webhook with data: {form_data}")
        
        message_body = form_data.get('Body', '')
        from_number = form_data.get('From', '')
        media_url = form_data.get('MediaUrl0', '')
        
        logger.info(f"Processing message from {from_number}")
        if media_url:
            logger.info(f"Media URL received: {media_url}")
            reply = process_audio_message(media_url)
        else:
            logger.info(f"Processing text message: {message_body}")
            reply = process_chat_message(message_body)
        
        resp = MessagingResponse()
        resp.message(reply)
        
        response_text = str(resp)
        logger.info(f"Sending response: {response_text}")
        return response_text, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"SMS handling failed: {str(e)}", exc_info=True)
        resp = MessagingResponse()
        resp.message(f"Sorry, something went wrong. Error: {str(e)}")
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

# For local development
if __name__ == '__main__':
    app.run(debug=True)