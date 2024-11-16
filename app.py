from flask import Flask, request, jsonify
from api.sms_handler import SMSHandler
import asyncio
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
sms_handler = SMSHandler()

@app.route("/test", methods=['GET'])
def test():
    """Test endpoint to verify server is running"""
    return jsonify({
        "status": "ok",
        "message": "Server is running"
    })

@app.route("/sms", methods=['POST'])
def handle_sms():
    """Handle incoming SMS webhooks from Twilio"""
    try:
        # Log the incoming request
        logger.info("Received webhook from Twilio")
        
        # Get the message data from Twilio's request
        webhook_data = request.form.to_dict(flat=False)
        logger.info(f"Webhook data: {webhook_data}")
        
        # Use asyncio to handle the async SMS handler
        logger.info("Processing message...")
        response = asyncio.run(sms_handler.handle_incoming_message(webhook_data))
        
        logger.info("Successfully processed message")
        return response, 200, {'Content-Type': 'application/xml'}
    
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}", exc_info=True)
        return (
            '<?xml version="1.0" encoding="UTF-8"?><Response>'
            '<Message>Sorry, an error occurred.</Message></Response>',
            500,
            {'Content-Type': 'application/xml'}
        )

if __name__ == "__main__":
    # Log startup
    logger.info("Starting Flask server...")
    app.run(debug=True, port=8000)