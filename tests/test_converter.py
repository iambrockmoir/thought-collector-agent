import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv
import binascii
import json

load_dotenv()

# Twilio credentials
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')

print("Connecting to Twilio...")
client = Client(account_sid, auth_token)

# Get recent messages with media
messages = client.messages.list(limit=20)
media_message = None

for msg in messages:
    if msg.num_media and int(msg.num_media) > 0:
        media_message = msg
        break

if not media_message:
    print("No messages with media found in recent messages!")
    exit(1)

print(f"Found message with media from: {media_message.from_}")
print(f"Message SID: {media_message.sid}")

# Get the media list
media_list = client.messages(media_message.sid).media.list()
if not media_list:
    print("No media found in message!")
    exit(1)

media = media_list[0]
print(f"\nMedia properties:")
media_properties = vars(media)
for prop in media_properties:
    if not prop.startswith('_'):
        print(f"{prop}: {getattr(media, prop)}")

# Get the media content using Twilio's fetch method
print("\nFetching media content...")
media_instance = client.messages(media_message.sid).media(media.sid).fetch()

# Construct the direct media URL
media_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{media_message.sid}/Media/{media.sid}"
print(f"Media URL: {media_url}")

# Download the content
print("Downloading media content...")
response = requests.get(
    media_url,
    auth=(account_sid, auth_token),
    headers={
        'Accept': 'audio/amr',
    },
    allow_redirects=True  # Follow redirects
)

if response.status_code != 200:
    print(f"Failed to download media content: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response: {response.text[:200]}")
    exit(1)

print(f"Response headers: {dict(response.headers)}")
print(f"Downloaded media size: {len(response.content)} bytes")
print("First 32 bytes of content:")
print(binascii.hexlify(response.content[:32]).decode())

# Save it locally
with open('test.amr', 'wb') as f:
    f.write(response.content)

print("Saved test.amr")

# Try to read the file back to verify
with open('test.amr', 'rb') as f:
    content = f.read()
    print(f"File size after save: {len(content)} bytes")
    print("First 32 bytes from saved file:")
    print(binascii.hexlify(content[:32]).decode())

print("\nNow testing converter...")

# Test the converter
with open('test.amr', 'rb') as f:
    files = {'audio': ('test.amr', f, 'audio/amr')}
    converter_response = requests.post(
        'https://audio-converter-service-production.up.railway.app/convert',
        files=files
    )

print(f"Converter Status: {converter_response.status_code}")
if converter_response.status_code != 200:
    print(f"Conversion failed: {converter_response.text}")
else:
    # Save the converted MP3
    with open('test.mp3', 'wb') as f:
        f.write(converter_response.content)
    print("Saved converted file as test.mp3")