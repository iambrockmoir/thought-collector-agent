import os
import requests
from dotenv import load_dotenv
import logging
import json

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def test_basic_message():
    """Test sending a basic text message"""
    webhook_data = {
        'MessageSid': 'TEST123',
        'From': '+1234567890',
        'To': '+1987654321',
        'Body': 'Hello, this is a test message',
        'NumMedia': '0'
    }
    
    try:
        logger.info("Sending test message...")
        logger.debug(f"Webhook data: {webhook_data}")
        
        response = requests.post(
            'http://localhost:8000/sms',
            data=webhook_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response body: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error("Test failed with exception:", exc_info=True)
        return False

def verify_server():
    """Verify the server is running and responding"""
    try:
        response = requests.get('http://localhost:8000/')
        logger.info(f"Server health check status: {response.status_code}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to server")
        return False

if __name__ == "__main__":
    if not verify_server():
        logger.error("Server is not responding")
        exit(1)
        
    logger.info("Starting Twilio webhook test...")
    
    if test_basic_message():
        logger.info("Test completed successfully")
    else:
        logger.error("Test failed")