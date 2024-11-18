from flask import Flask, jsonify, request
from twilio.twiml.messaging_response import MessagingResponse
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # This ensures logs go to Vercel
)
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
        form_data = request.form.to_dict()
        logger.info(f"Received SMS webhook with data: {form_data}")
        
        message_body = form_data.get('Body', '')
        from_number = form_data.get('From', '')
        logger.info(f"Processing message '{message_body}' from {from_number}")
        
        resp = MessagingResponse()
        resp.message("Thanks for your message! I'm currently being updated.")
        
        response_text = str(resp)
        logger.info(f"Sending response: {response_text}")
        return response_text, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"SMS handling failed: {str(e)}", exc_info=True)
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again later.")
        return str(resp), 200, {'Content-Type': 'text/xml'}

# For local development
if __name__ == '__main__':
    app.run(debug=True)