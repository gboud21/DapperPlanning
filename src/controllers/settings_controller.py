from src.events import (
    EventDispatcher, UISettingsDialogOpenRequestedEvent, UISettingsSaveRequestedEvent,
    AppThemeChangedEvent, UITemplateConfigExportRequestedEvent, UIErrorNotificationEvent
)
from src.utils.theme_manager import ThemeManager
from src.views.settings_dialog import SettingsDialog
from src.utils.paths import get_user_data_dir, get_app_config_dir
import tkinter as tk
import os
import json

class SettingsController:
    def __init__(self, root: tk.Tk, dispatcher: EventDispatcher):
        """
        Initializes the SettingsController.

        Args:
            root (tk.Tk): The root Tkinter window.
            dispatcher (EventDispatcher): The application's event dispatcher.
        """
        self.root = root
        self.dispatcher = dispatcher
        
        self._subscribe_events()

    def _subscribe_events(self):
        self.dispatcher.subscribe(UISettingsDialogOpenRequestedEvent, self.handle_open_dialog)
        self.dispatcher.subscribe(UISettingsSaveRequestedEvent, self.handle_save_settings)
        self.dispatcher.subscribe(UITemplateConfigExportRequestedEvent, self.handle_template_export)

    def handle_open_dialog(self, event: UISettingsDialogOpenRequestedEvent):
        current_settings = ThemeManager.get_general_settings()
        SettingsDialog(self.root, self.dispatcher, current_settings)

    def handle_save_settings(self, event: UISettingsSaveRequestedEvent):
        # Check if theme changed for live update
        current_settings = ThemeManager.get_general_settings()
        old_theme = current_settings.get('theme', 'dark')
        
        ThemeManager.save_general_settings(
            theme=event.theme,
            auto_save=event.auto_save,
            log_level=event.log_level,
            templates=event.templates
        )

        if old_theme != event.theme:
            is_dark = (event.theme.lower() == 'dark')
            self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=is_dark))
            ThemeManager.apply_ttk_theme(is_dark)

    def handle_template_export(self, event: UITemplateConfigExportRequestedEvent):
        """
        Handles the export of the template configuration to a JSON file.
        """
        try:
            # Use OS-appropriate user data directory for exports
            output_dir = get_user_data_dir() / "output"
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = output_dir / "template_config.json"
            
            # Note: If default_templates.json were to be loaded as a base,
            # it should be accessed via: get_app_config_dir() / 'default_templates.json'
            
            with open(file_path, 'w') as f:
                json.dump(event.payload, f, indent=4)
                
            self.dispatcher.dispatch(UIErrorNotificationEvent(
                title="Export Successful",
                message=f"Template configuration saved to {file_path}"
            ))
        except Exception as e:
            self.dispatcher.dispatch(UIErrorNotificationEvent(
                title="Export Failed",
                message=f"Could not save template configuration: {str(e)}"
            ))
