import pytest
from unittest.mock import MagicMock, patch
from src.infrastructure.api.ai_client import GenericLLMClient
import json
import io

@pytest.fixture
def client_setup():
    context = MagicMock()
    settings = MagicMock()
    context.resolve.return_value = settings
    
    settings.get.side_effect = lambda key, default: {
        'ai_api_key': 'test-key',
        'ai_endpoint': 'https://example.com/{model}',
        'ai_model': 'test-model'
    }.get(key, default)
    
    client = GenericLLMClient(context)
    return client, settings

def test_send_chat_turn_success(client_setup):
    client, settings = client_setup
    
    mock_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "estimated_hours": 12.5,
                                "reasoning": "This is a test reasoning."
                            })
                        }
                    ]
                }
            }
        ]
    }
    
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_resp.getcode.return_value = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        result = client.send_chat_turn([{"role": "user", "parts": [{"text": "hello"}]}])
        
        assert result['estimated_hours'] == 12.5
        assert result['reasoning'] == "This is a test reasoning."

def test_send_chat_turn_error(client_setup):
    client, settings = client_setup
    
    with patch('urllib.request.urlopen', side_effect=Exception("Network error")):
        result = client.send_chat_turn([])
        
        assert result['estimated_hours'] == 0.0
        assert "Network error" in result['reasoning']
