import json
import os
from tkinter import ttk
from src.utils.paths import get_user_data_dir

class ThemeManager:
    @classmethod
    def _get_settings_path(cls):
        """Returns the absolute path to the settings.json file in the user data directory."""
        return get_user_data_dir() / 'settings.json'
    
    # VS Code-style color palettes
    DARK_PALETTE = {
        'bg': '#1e1e1e',
        'field_bg': '#252526',
        'fg': '#d4d4d4',
        'highlight': '#094771'
    }
    
    LIGHT_PALETTE = {
        'bg': '#f0f0f0',
        'field_bg': '#ffffff',
        'fg': '#000000',
        'highlight': '#0078d7'
    }

    @classmethod
    def get_default_settings(cls):
        return {
            'is_dark': False,
            'theme': 'dark',
            'auto_save': False,
            'log_level': 'INFO',
            'templates': {
                'Epic': {'Default': ''},
                'Feature': {'Default': ''},
                'Story': {'Default': ''}
            },
            # Template parameters
            'target_tool': 'GitLab',
            'methodology': 'Scrum',
            'hierarchy': 'Epic -> Feature -> Story',
            'description_type': 'Heavyweight',
            'include_out_of_scope': False,
            'include_compliance': False,
            
            'auth_url': '',
            'auth_pat': '',
            'epic_group_id': '',
            'product_mappings': {},
            'capabilities': []
        }

    @classmethod
    def load_settings(cls) -> bool:
        """Loads the is_dark setting."""
        settings = cls.load_all_settings()
        return settings.get('is_dark', False)

    @classmethod
    def load_all_settings(cls) -> dict:
        """Loads all settings from the settings file."""
        settings_path = cls._get_settings_path()
        if not os.path.exists(settings_path):
            cls.save_all_settings(cls.get_default_settings())
            return cls.get_default_settings()
        try:
            with open(settings_path, 'r') as f:
                settings = cls.get_default_settings()
                settings.update(json.load(f))
                return settings
        except (json.JSONDecodeError, IOError):
            return cls.get_default_settings()

    @classmethod
    def save_settings(cls, is_dark: bool):
        """Saves the is_dark setting."""
        settings = cls.load_all_settings()
        settings['is_dark'] = is_dark
        settings['theme'] = 'dark' if is_dark else 'light'
        cls.save_all_settings(settings)

    @classmethod
    def save_all_settings(cls, settings: dict):
        """Saves the provided settings dictionary to the settings file."""
        settings_path = cls._get_settings_path()
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)

    @classmethod
    def get_integration_settings(cls) -> dict:
        """Retrieves only the integration-related settings."""
        settings = cls.load_all_settings()
        return {
            'auth_url': settings.get('auth_url', ''),
            'auth_pat': settings.get('auth_pat', ''),
            'epic_group_id': settings.get('epic_group_id', ''),
            'product_mappings': settings.get('product_mappings', {}),
            'capabilities': settings.get('capabilities', [])
        }

    @classmethod
    def save_integration_settings(cls, auth_url: str, auth_pat: str, epic_group_id: str, product_mappings: dict, capabilities: list):
        """Saves integration-related settings."""
        settings = cls.load_all_settings()
        settings.update({
            'auth_url': auth_url,
            'auth_pat': auth_pat,
            'epic_group_id': epic_group_id,
            'product_mappings': product_mappings,
            'capabilities': capabilities
        })
        cls.save_all_settings(settings)

    @classmethod
    def get_general_settings(cls) -> dict:
        """Retrieves general application preferences and templates."""
        settings = cls.load_all_settings()
        return {
            'theme': settings.get('theme', 'dark'),
            'auto_save': settings.get('auto_save', False),
            'log_level': settings.get('log_level', 'INFO'),
            'templates': settings.get('templates', cls.get_default_settings()['templates']),
            'target_tool': settings.get('target_tool', 'GitLab'),
            'methodology': settings.get('methodology', 'Scrum'),
            'hierarchy': settings.get('hierarchy', 'Epic -> Feature -> Story'),
            'description_type': settings.get('description_type', 'Heavyweight'),
            'include_out_of_scope': settings.get('include_out_of_scope', False),
            'include_compliance': settings.get('include_compliance', False)
        }

    @classmethod
    def save_general_settings(cls, theme: str, auto_save: bool, log_level: str, templates: dict, **kwargs):
        """Saves general application preferences and templates."""
        settings = cls.load_all_settings()
        settings.update({
            'theme': theme,
            'is_dark': True if theme.lower() == 'dark' else False,
            'auto_save': auto_save,
            'log_level': log_level,
            'templates': templates
        })
        # Update any additional parameters (tool, methodology, etc.)
        settings.update(kwargs)
        cls.save_all_settings(settings)

    @classmethod
    def apply_ttk_theme(cls, is_dark: bool):
        palette = cls.DARK_PALETTE if is_dark else cls.LIGHT_PALETTE
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure global ttk elements
        style.configure('.', background=palette['bg'], foreground=palette['fg'])
        style.configure('TFrame', background=palette['bg'])
        style.configure('TLabel', background=palette['bg'], foreground=palette['fg'])
        style.configure('TButton', background=palette['field_bg'], foreground=palette['fg'])
        style.map('TButton', background=[('active', palette['highlight'])])
        
        style.configure('Treeview', 
                        background=palette['field_bg'], 
                        foreground=palette['fg'], 
                        fieldbackground=palette['field_bg'],
                        borderwidth=0)
        style.map('Treeview', background=[('selected', palette['highlight'])])
        
        style.configure('TCombobox', 
                        fieldbackground=palette['field_bg'], 
                        background=palette['field_bg'], 
                        foreground=palette['fg'],
                        arrowcolor='white' if is_dark else 'black')
        
        # Special style for Preferences/Settings with forced high-contrast black text
        style.configure('Preferences.TCombobox', 
                        fieldbackground='white', 
                        background='white', 
                        foreground='black',
                        arrowcolor='black')
        style.map('Preferences.TCombobox', 
                  fieldbackground=[('readonly', 'white')],
                  foreground=[('readonly', 'black')])
        
        style.configure('TNotebook', background=palette['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=palette['bg'], foreground=palette['fg'])
        style.map('TNotebook.Tab', background=[('selected', palette['field_bg'])])

        style.configure('TLabelframe', background=palette['bg'], foreground=palette['fg'])
        style.configure('TLabelframe.Label', background=palette['bg'], foreground=palette['fg'])

        style.configure('TEntry', fieldbackground=palette['field_bg'], foreground=palette['fg'])
        style.configure('TScrollbar', background=palette['bg'], troughcolor=palette['field_bg'], borderwidth=0)
