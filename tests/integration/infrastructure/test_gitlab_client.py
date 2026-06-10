import pytest
import json
from io import BytesIO
from src.infrastructure.api.gitlab_client import GitLabClient

@pytest.fixture
def mock_gitlab_client():
    return GitLabClient(base_url="https://fake.gitlab.com", token="fake_token", group_id="999", project_id="888")

def test_gitlab_client_request_parsing(mocker, mock_gitlab_client):
    """Verifies the client can parse a successful API response without hitting the network."""
    # 1. Define the fake data GitLab would normally return
    fake_response_data = [{"id": 101, "iid": 1, "title": "Mock Remote Epic"}]
    fake_response_bytes = json.dumps(fake_response_data).encode('utf-8')
    
    # 2. Mock urllib's urlopen to return our fake bytes
    mock_response = mocker.MagicMock()
    mock_response.read.return_value = fake_response_bytes
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response
    mocker.patch('urllib.request.urlopen', return_value=mock_response)
    
    # 3. Execute the client method (e.g., a generic GET request)
    result = mock_gitlab_client._request("groups/999/epics")
    
    # 4. Assert the client correctly decoded the byte response into a Python list/dict
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Mock Remote Epic"
