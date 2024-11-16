import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Your Account SID and Auth Token
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

def test_send_audio():
    # Send a message with audio
    message = client.messages.create(
        body="Test audio message",
        from_=os.getenv('TWILIO_PHONE_NUMBER'),
        to=os.getenv('TEST_PHONE_NUMBER'),  # Your verified phone number
        media_url=['https://demo.twilio.com/docs/voice.mp3']
    )
    
    print(f"Message sent! SID: {message.sid}")

if __name__ == "__main__":
    test_send_audio()