import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Now we can import our modules
from api.transcription import AudioProcessor
from lib.config import get_settings

load_dotenv()
settings = get_settings()

async def test_audio_processing():
    logger.info("Starting audio processing test...")
    
    # Initialize processor
    processor = AudioProcessor()
    
    # Test audio URL (Twilio's sample audio)
    test_url = "https://demo.twilio.com/docs/classic.mp3"
    
    # Twilio auth
    auth = (settings.twilio_account_sid, settings.twilio_auth_token)
    
    try:
        # Process audio
        logger.info("Processing audio from URL: %s", test_url)
        result = await processor.process_audio_message(
            media_url=test_url,
            user_phone="+1234567890",
            auth=auth
        )
        
        logger.info("Processing completed successfully")
        print("\nProcessing Result:")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"\nFull Transcription: {result['transcription']}")
        
    except Exception as e:
        logger.error("Error during audio processing: %s", str(e))
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_audio_processing())