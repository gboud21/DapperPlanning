import os
import sys
from pathlib import Path

def get_user_data_dir(app_name: str = 'DapperPlanning') -> Path:
    """
    Returns the OS-appropriate path for user-specific application data.
    
    Args:
        app_name (str): The name of the application.
        
    Returns:
        Path: The absolute path to the user data directory.
    """
    if sys.platform == 'win32':
        # Windows: %APPDATA% (Roaming)
        base = os.environ.get('APPDATA')
        if not base:
            base = Path.home() / 'AppData' / 'Roaming'
        data_dir = Path(base) / app_name
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Application Support
        data_dir = Path.home() / 'Library' / 'Application Support' / app_name
    else:
        # Linux/Other: XDG_CONFIG_HOME or ~/.config
        base = os.environ.get('XDG_CONFIG_HOME')
        if not base:
            base = Path.home() / '.config'
        data_dir = Path(base) / app_name
        
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_app_config_dir() -> Path:
    """
    Returns the absolute path to the application's read-only config directory.
    
    Returns:
        Path: The absolute path to the src/config directory.
    """
    # Dynamically resolve based on the location of this file (src/utils/paths.py)
    return Path(__file__).parent.parent / 'config'

def get_output_dir() -> Path:
    """
    Returns the absolute path to the output directory at the project root.
    Ensures the directory exists.
    
    Returns:
        Path: The absolute path to the output directory.
    """
    # Root is 3 levels up from src/utils/paths.py
    root = Path(__file__).parent.parent.parent
    output_dir = root / 'output'
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def get_logs_dir() -> Path:
    """Returns the absolute path to the logs directory at the project root."""
    root = Path(__file__).parent.parent.parent
    logs_dir = root / 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def get_audit_dir() -> Path:
    """Returns the absolute path to the audit directory at the project root."""
    root = Path(__file__).parent.parent.parent
    audit_dir = root / 'audit'
    os.makedirs(audit_dir, exist_ok=True)
    return audit_dir

# Global path constants
GITLAB_SYNC_OUTPUT_FILE = get_output_dir() / 'gitlab_integration.json'
