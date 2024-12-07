import pytest
from unittest.mock import AsyncMock, patch, MagicMock

def test_audio_webhook(test_client):
    """Test that audio messages are forwarded to Rails properly"""
    mock_form_data = {
        'From': '+1234567890',
        'MediaUrl0': 'https://fake-audio.com/audio.amr',
        'MediaContentType0': 'audio/amr'
    }
    
    # Create a mock response object
    mock_response = MagicMock()
    mock_response.status = 200
    
    # Create an async context manager that accepts self
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    with patch('aiohttp.ClientSession.post', return_value=AsyncContextManager()) as mock_post:
        response = test_client.post('/webhook', data=mock_form_data)
        
        # Should return valid TwiML
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        assert '<?xml version="1.0" encoding="UTF-8"?><Response />' in response_text
        
        # Should have called Rails service
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert 'from_number' in call_args['json']
        assert 'media_url' in call_args['json'] 