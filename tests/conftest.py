import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Mock both Supabase and Pinecone before importing app
import supabase
def mock_create_client(*args, **kwargs):
    mock_client = MagicMock()
    mock_client.table = MagicMock()
    mock_client.auth = MagicMock()
    return mock_client

supabase.create_client = mock_create_client

# Mock Pinecone
import pinecone
def mock_init(*args, **kwargs):
    return None

def mock_index(*args, **kwargs):
    mock_idx = MagicMock()
    mock_idx.upsert = AsyncMock()
    mock_idx.query = AsyncMock(return_value={'matches': []})
    return mock_idx

pinecone.init = mock_init
pinecone.Index = mock_index

# Add before app import
import api.settings
api.settings.vercel_url = "https://test-vercel-url.com"

# Now we can safely import the app
from api.routes import app

@pytest.fixture
def test_client():
    app.config['TESTING'] = True
    return app.test_client() 

@pytest.fixture
async def mock_storage_service():
    with patch('api.services.storage.StorageService') as mock:
        mock.store_thought = AsyncMock(return_value={'id': 'test-id'})
        yield mock

@pytest.fixture
async def mock_chat_service():
    with patch('api.services.chat.ChatService') as mock:
        mock.process_message = AsyncMock(return_value="Test response")
        yield mock

@pytest.fixture
async def mock_sms_service():
    with patch('api.services.sms.SMSService') as mock:
        mock.send_message = AsyncMock()
        yield mock 