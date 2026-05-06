import json
import os
from tkinter import ttk

class ThemeManager:
    SETTINGS_FILE = 'settings.json'
    
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
    def load_settings(cls) -> bool:
        if not os.path.exists(cls.SETTINGS_FILE):
            cls.save_settings(False)
            return False
        try:
            with open(cls.SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('is_dark', False)
        except (json.JSONDecodeError, IOError):
            return False

    @classmethod
    def save_settings(cls, is_dark: bool):
        settings = {'is_dark': is_dark}
        with open(cls.SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)

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
                        foreground=palette['fg'])
        
        style.configure('TNotebook', background=palette['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=palette['bg'], foreground=palette['fg'])
        style.map('TNotebook.Tab', background=[('selected', palette['field_bg'])])

        style.configure('TLabelframe', background=palette['bg'], foreground=palette['fg'])
        style.configure('TLabelframe.Label', background=palette['bg'], foreground=palette['fg'])

        style.configure('TEntry', fieldbackground=palette['field_bg'], foreground=palette['fg'])
        style.configure('TScrollbar', background=palette['bg'], troughcolor=palette['field_bg'], borderwidth=0)
