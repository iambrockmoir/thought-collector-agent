import os
import sys
from pathlib import Path
import logging
from twilio.rest import Client
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def test_twilio_setup():
    """Test Twilio credentials and phone number setup"""
    
    # Get credentials from environment
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
    test_number = os.getenv('TEST_PHONE_NUMBER')

    print("\nTwilio Configuration Check:")
    print("-" * 50)
    
    # Check if all required variables are set
    if not all([account_sid, auth_token, twilio_number]):
        print("❌ Missing required environment variables")
        print(f"TWILIO_ACCOUNT_SID: {'✓' if account_sid else '❌'}")
        print(f"TWILIO_AUTH_TOKEN: {'✓' if auth_token else '❌'}")
        print(f"TWILIO_PHONE_NUMBER: {'✓' if twilio_number else '❌'}")
        return

    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Verify account
        account = client.api.accounts(account_sid).fetch()
        print(f"✓ Account verified: {account.friendly_name}")
        print(f"✓ Account status: {account.status}")
        
        # Check phone number
        numbers = client.incoming_phone_numbers.list(phone_number=twilio_number)
        if numbers:
            print(f"✓ Phone number verified: {twilio_number}")
            number = numbers[0]
            print(f"✓ SMS enabled: {number.capabilities['sms']}")
            print(f"✓ Voice enabled: {number.capabilities['voice']}")
        else:
            print(f"❌ Phone number not found in account: {twilio_number}")
        
        # Try sending a test message
        if test_number:
            print("\nSending test message...")
            try:
                message = client.messages.create(
                    body="🤖 Test message from Thought Collector",
                    from_=twilio_number,
                    to=test_number
                )
                print(f"✓ Test message sent! SID: {message.sid}")
            except Exception as e:
                print(f"❌ Failed to send test message: {str(e)}")
        else:
            print("\n⚠️ No TEST_PHONE_NUMBER set in .env file")
            
    except Exception as e:
        print(f"❌ Error verifying Twilio setup: {str(e)}")

if __name__ == "__main__":
    test_twilio_setup()