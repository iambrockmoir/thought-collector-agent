import os
import requests
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

def test_send_message():
    # Initialize Twilio client
    client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )

    try:
        # Send a message
        message = client.messages.create(
            body="Test message",
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            to=os.getenv('TEST_PHONE_NUMBER')  # Your verified phone number
        )
        print(f"Message sent! SID: {message.sid}")
        
    except Exception as e:
        print(f"Error sending message: {str(e)}")

def test_webhook_locally():
    # Simulate a Twilio webhook to your local server
    webhook_data = {
        'MessageSid': 'TEST123',
        'From': '+1234567890',
        'To': os.getenv('TWILIO_PHONE_NUMBER'),
        'Body': 'Test message from local simulation',
        'NumMedia': '0'
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/sms',
            data=webhook_data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error testing webhook: {str(e)}")

if __name__ == "__main__":
    # Choose which test to run
    print("1. Test sending message via Twilio")
    print("2. Test webhook locally")
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "1":
        test_send_message()
    elif choice == "2":
        test_webhook_locally()
    else:
        print("Invalid choice")