import os
from twilio.rest import Client
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def check_twilio_setup():
    # Get credentials
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    client = Client(account_sid, auth_token)
    
    # Get account details
    account = client.api.accounts(account_sid).fetch()
    print(f"\nAccount Status:")
    print(f"Type: {account.type}")
    print(f"Status: {account.status}")
    
    # Check outgoing caller IDs (verified numbers)
    print("\nVerified Numbers:")
    verified_numbers = client.outgoing_caller_ids.list()
    if verified_numbers:
        for number in verified_numbers:
            print(f"- {number.phone_number}")
    else:
        print("No verified numbers found")
    
    # Check balance
    balance = client.api.accounts(account_sid).balance.fetch()
    print(f"\nAccount Balance:")
    print(f"Current balance: ${balance.balance}")
    print(f"Currency: {balance.currency}")

    # List recent messages with errors
    print("\nRecent Messages with Errors:")
    messages = client.messages.list(limit=5)
    for msg in messages:
        if msg.status in ['failed', 'undelivered']:
            print(f"\nMessage {msg.sid}:")
            print(f"- To: {msg.to}")
            print(f"- From: {msg.from_}")
            print(f"- Status: {msg.status}")
            print(f"- Error Code: {msg.error_code}")
            print(f"- Error Message: {msg.error_message}")

if __name__ == "__main__":
    check_twilio_setup()