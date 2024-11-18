from flask import Flask, jsonify, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
import logging
import sys
import os
from openai import OpenAI

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

try:
    client = OpenAI(api_key=openai_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}", exc_info=True)
    client = None

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
        
        logger.info(f"Processing message '{message_body}' from {from_number}")
        if media_url:
            logger.info(f"Media URL received: {media_url}")
            reply = "I see you sent me some media! I'll be able to process that soon."
        else:
            logger.info("Calling process_chat_message")
            reply = process_chat_message(message_body)
            logger.info(f"Received reply from process_chat_message: {reply}")
        
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