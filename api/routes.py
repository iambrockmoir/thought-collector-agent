from flask import Flask, jsonify, request
from twilio.twiml.messaging_response import MessagingResponse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

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

@app.route('/debug')
def debug_info():
    """Debug endpoint"""
    try:
        import sys
        return jsonify({
            "python_version": sys.version,
            "endpoints": [
                {"path": "/", "methods": ["GET"]},
                {"path": "/debug", "methods": ["GET"]},
                {"path": "/api/sms", "methods": ["POST"]}
            ]
        })
    except Exception as e:
        logger.error(f"Debug info failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sms', methods=['POST'])
def handle_sms():
    """Handle incoming SMS messages"""
    try:
        logger.info("Received SMS webhook")
        # Create TwiML response
        resp = MessagingResponse()
        resp.message("Thanks for your message! I'm currently being updated, please try again in a few minutes.")
        
        return str(resp), 200, {'Content-Type': 'text/xml'}
    except Exception as e:
        logger.error(f"SMS handling failed: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again later.")
        return str(resp), 200, {'Content-Type': 'text/xml'}

# For local development
if __name__ == '__main__':
    app.run(debug=True)