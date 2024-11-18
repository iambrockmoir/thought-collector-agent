import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
import pytest
from unittest.mock import patch, MagicMock

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

@pytest.mark.asyncio
async def test_audio_processing():
    """Test the complete audio processing flow"""
    processor = AudioProcessor()
    
    # Mock responses
    mock_twilio_response = MagicMock()
    mock_twilio_response.status_code = 200
    mock_twilio_response.content = b"fake_audio_data"
    
    mock_converter_response = MagicMock()
    mock_converter_response.status_code = 200
    mock_converter_response.content = b"fake_mp3_data"
    
    with patch('requests.get', return_value=mock_twilio_response), \
         patch('requests.post', return_value=mock_converter_response), \
         patch('openai.audio.transcriptions.create', return_value="Test transcription"):
        
        result = await processor.process_audio_message(
            media_url="https://fake-url.com/audio.amr",
            user_phone="+1234567890"
        )
        
        assert result["transcription"] == "Test transcription"
        assert "I heard: Test transcription" in result["message"]

if __name__ == "__main__":
    asyncio.run(test_audio_processing())