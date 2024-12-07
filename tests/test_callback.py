import pytest
from unittest.mock import AsyncMock, patch

def test_audio_callback(test_client):
    """Test handling of transcription callback from Rails"""
    callback_data = {
        'from_number': '+1234567890',
        'transcription': 'Remember to buy milk and eggs'
    }
    
    # Create async mocks with predefined return values
    mock_store = AsyncMock(return_value={'id': 'test-id'})
    mock_chat = AsyncMock(return_value="Got it! I'll remember you need milk and eggs.")
    mock_sms = AsyncMock()
    
    with patch('api.services.storage.StorageService.store_thought', mock_store), \
         patch('api.services.chat.ChatService.process_message', mock_chat), \
         patch('api.services.sms.SMSService.send_message', mock_sms):
        
        response = test_client.post(
            '/audio-callback',
            json=callback_data
        )
        
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        
        # Verify the flow
        mock_store.assert_awaited_once_with(
            callback_data['from_number'],
            callback_data['transcription']
        )
        
        # Verify chat service call with exact parameters
        mock_chat.assert_called_once()
        call_args = mock_chat.call_args
        assert call_args.kwargs['from_number'] == callback_data['from_number']
        assert call_args.kwargs['message'] == callback_data['transcription']

def test_audio_callback_error(test_client):
    """Test handling of error callback from Rails"""
    error_data = {
        'from_number': '+1234567890',
        'error': 'Failed to process audio'
    }
    
    with patch('api.services.sms.SMSService.send_message', new_callable=AsyncMock) as mock_sms:
        response = test_client.post(
            '/audio-callback',
            json=error_data
        )
        
        assert response.status_code == 200
        assert response.json['status'] == 'error handled'
        mock_sms.assert_awaited_once() 