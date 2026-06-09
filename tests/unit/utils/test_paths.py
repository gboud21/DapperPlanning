import pytest
from pathlib import Path
from src.utils.paths import get_user_data_dir, get_app_config_dir

def test_get_user_data_dir():
    """Verifies the user data directory is correctly resolved as a Path object."""
    data_dir = get_user_data_dir()
    assert isinstance(data_dir, Path)
    assert data_dir.name == "DapperPlanning" or data_dir.name == "output"

def test_get_app_config_dir():
    """Verifies the app config directory is properly located."""
    config_dir = get_app_config_dir()
    assert isinstance(config_dir, Path)
    assert "src" in str(config_dir) and "config" in str(config_dir)
