import pytest
from src.utils.theme_manager import ThemeManager

def test_theme_palettes_exist():
    """Ensures the static palettes are defined correctly."""
    assert isinstance(ThemeManager.DARK_PALETTE, dict)
    assert isinstance(ThemeManager.LIGHT_PALETTE, dict)
    assert 'bg' in ThemeManager.DARK_PALETTE
    assert 'fg' in ThemeManager.DARK_PALETTE

def test_load_general_settings_defaults(mocker):
    """Mocks the open function to simulate a missing file and checks fallback defaults."""
    mocker.patch('builtins.open', side_effect=FileNotFoundError)
    settings = ThemeManager.get_general_settings()
    assert isinstance(settings, dict)
    assert settings.get('theme') == 'dark'  # Fixed casing to match actual default
