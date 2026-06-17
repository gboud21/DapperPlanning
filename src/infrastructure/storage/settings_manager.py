import json
import os
from src.utils.paths import get_user_data_dir

class SettingsManager:
    """
    Manages application settings, providing persistence and access to configuration.
    """
    def __init__(self):
        self.settings_path = get_user_data_dir() / 'settings.json'
        self._settings = self._get_default_settings()
        self.load()

    def _get_default_settings(self) -> dict:
        return {
            'is_dark': False,
            'theme': 'dark',
            'auto_save': False,
            'log_level': 'INFO',
            'show_status_in_tree': True,
            'last_workspace': None,
            'window_maximized': False,
            'templates': {
                'Epic': {'Default': ''},
                'Feature': {'Default': ''},
                'Story': {'Default': ''}
            },
            'target_tool': 'GitLab',
            'methodology': 'Scrum',
            'hierarchy': 'Epic -> Feature -> Story',
            'description_type': 'Heavyweight',
            'include_out_of_scope': False,
            'include_compliance': False,
            'last_selected_item_type': 'Epic',
            'selected_templates': {
                'Epic': 'Default',
                'Feature': 'Default',
                'Story': 'Default'
            },
            'auth_url': '',
            'auth_pat': '',
            'epic_group_id': '',
            'product_mappings': {},
            'capabilities': [],
            'utilization_factor': 100,
            'ai_api_key': '',
            'ai_endpoint': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            'ai_model': 'gemini-1.5-flash'
        }

    def load(self):
        """Loads settings from settings.json if it exists."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
                    self._settings.update(data)
            except (json.JSONDecodeError, IOError):
                pass

    def get(self, key: str, default: any = None) -> any:
        """Retrieves a setting value by key."""
        return self._settings.get(key, default)

    def set(self, key: str, value: any):
        """Sets a setting value for the given key."""
        self._settings[key] = value

    def save(self):
        """Writes the current settings back to settings.json."""
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        with open(self.settings_path, 'w') as f:
            json.dump(self._settings, f, indent=4)
