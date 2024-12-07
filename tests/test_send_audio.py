import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

def test_real_audio():
    client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )
    
    message = client.messages.create(
        to=os.getenv('TEST_PHONE_NUMBER'),
        from_=os.getenv('TWILIO_PHONE_NUMBER'),
        body="Testing audio processing",
        media_url=['https://demo.twilio.com/docs/voice.mp3']
    )
    
    print(f"Test message sent! SID: {message.sid}")

if __name__ == "__main__":
    test_real_audio()