import pytest
import os
import sys
from pathlib import Path

# Add project root to sys.path to resolve 'src' imports
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture
def mock_workspace_dir(tmp_path):
    """Provides a temporary directory to simulate the user data path."""
    return tmp_path
