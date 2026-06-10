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

@pytest.fixture
def headless_tk():
    """Provides a hidden Tkinter root for UI testing, safely destroying it after."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    try:
        root.update()
        root.destroy()
    except:
        pass
