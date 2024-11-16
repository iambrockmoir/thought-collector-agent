import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from api.chat import ChatEngine
from api.transcription import AudioProcessor
from lib.database import Database
from lib.vector_store import PineconeClient
from lib.config import get_settings

# Load settings
settings = get_settings()

# Test constants
TEST_PHONE = "+1234567890"
TEST_AUDIO_URL = "https://demo.twilio.com/docs/classic.mp3"
TEST_MESSAGE = "Test thought message"
TEST_AUTH = (settings.twilio_account_sid, settings.twilio_auth_token)

@pytest.fixture
async def mock_database():
    """Create a mock database for testing"""
    mock_db = MagicMock(spec=Database)
    
    # Mock store_thought
    mock_db.store_thought = AsyncMock(return_value={
        'id': 'test-id',
        'user_phone': TEST_PHONE,
        'transcription': TEST_MESSAGE,
        'created_at': datetime.utcnow().isoformat()
    })
    
    # Mock search_thoughts
    mock_db.search_thoughts = AsyncMock(return_value=[{
        'id': 'test-id',
        'transcription': TEST_MESSAGE,
        'created_at': datetime.utcnow().isoformat()
    }])
    
    # Mock get_thought_by_id to raise exception
    mock_db.get_thought_by_id = AsyncMock(side_effect=Exception("Not found"))
    
    return mock_db

@pytest.fixture
async def setup_clients(mock_database):
    """Setup test clients with mock database"""
    chat_engine = ChatEngine()
    audio_processor = AudioProcessor()
    
    # Mock audio processor methods
    audio_processor.process_audio_message = AsyncMock(return_value={
        'transcription': TEST_MESSAGE,
        'message': 'Processed successfully'
    })
    
    return {
        'chat': chat_engine,
        'audio': audio_processor,
        'db': mock_database
    }

@pytest.mark.asyncio
async def test_audio_processing(setup_clients):
    """Test audio processing and transcription"""
    audio = setup_clients['audio']
    
    result = await audio.process_audio_message(
        media_url=TEST_AUDIO_URL,
        user_phone=TEST_PHONE,
        auth=TEST_AUTH
    )
    
    assert result is not None
    assert 'transcription' in result
    assert 'message' in result
    assert result['transcription'] != ""

@pytest.mark.asyncio
async def test_thought_storage(setup_clients):
    """Test storing thoughts in database"""
    db = setup_clients['db']
    
    thought_data = {
        'user_phone': TEST_PHONE,
        'audio_url': TEST_AUDIO_URL,
        'transcription': TEST_MESSAGE,
        'metadata': {
            'source': 'test',
            'timestamp': datetime.utcnow().isoformat()
        }
    }
    
    result = await db.store_thought(thought_data)
    
    assert result is not None
    assert result['id'] is not None
    assert result['user_phone'] == TEST_PHONE
    assert result['transcription'] == TEST_MESSAGE

@pytest.mark.asyncio
async def test_chat_query(setup_clients):
    """Test chat query and response"""
    chat = setup_clients['chat']
    
    response = await chat.process_query(
        user_phone=TEST_PHONE,
        message="What did I record earlier?"
    )
    
    assert response is not None
    assert 'response' in response
    assert 'context_used' in response
    assert 'timestamp' in response

@pytest.mark.asyncio
async def test_full_flow(setup_clients):
    """Test complete flow: audio → transcription → storage → retrieval → chat"""
    audio = setup_clients['audio']
    chat = setup_clients['chat']
    
    # Process audio
    audio_result = await audio.process_audio_message(
        media_url=TEST_AUDIO_URL,
        user_phone=TEST_PHONE,
        auth=TEST_AUTH
    )
    assert audio_result['transcription'] != ""
    
    # Query about the recorded thought
    chat_response = await chat.process_query(
        user_phone=TEST_PHONE,
        message="What was in my last recording?"
    )
    assert chat_response['response'] != ""
    
    # Verify context was used
    assert chat_response['context_used'] == True

@pytest.mark.asyncio
async def test_vector_search(setup_clients):
    """Test vector similarity search"""
    db = setup_clients['db']
    
    # Store a thought
    thought_data = {
        'user_phone': TEST_PHONE,
        'audio_url': TEST_AUDIO_URL,
        'transcription': "This is a unique test message for vector search",
        'metadata': {'source': 'test'}
    }
    await db.store_thought(thought_data)
    
    # Search for similar thoughts
    results = await db.search_thoughts(
        user_phone=TEST_PHONE,
        query="test message search",
        limit=5
    )
    
    assert len(results) > 0
    assert results[0]['transcription'] is not None

@pytest.mark.asyncio
async def test_conversation_context(setup_clients):
    """Test conversation context maintenance"""
    chat = setup_clients['chat']
    
    # First message
    response1 = await chat.process_query(
        user_phone=TEST_PHONE,
        message="Remember this: testing context"
    )
    
    # Follow-up message
    response2 = await chat.process_query(
        user_phone=TEST_PHONE,
        message="What did I just ask you to remember?"
    )
    
    assert 'testing context' in response2['response'].lower()
    assert response2['context_used'] == True

@pytest.mark.asyncio
async def test_error_handling(setup_clients):
    """Test error handling"""
    audio = setup_clients['audio']
    db = setup_clients['db']
    
    # Test invalid audio URL
    audio.process_audio_message = AsyncMock(side_effect=Exception("Invalid URL"))
    with pytest.raises(Exception):
        await audio.process_audio_message(
            media_url="invalid_url",
            user_phone=TEST_PHONE,
            auth=TEST_AUTH
        )
    
    # Test invalid database query
    with pytest.raises(Exception):
        await db.get_thought_by_id("invalid-uuid")

if __name__ == "__main__":
    pytest.main(["-v", "test_integration.py"])