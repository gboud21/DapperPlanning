from src.events import (
    EventDispatcher, UISettingsDialogOpenRequestedEvent, UISettingsSaveRequestedEvent,
    AppThemeChangedEvent
)
from src.utils.theme_manager import ThemeManager
from src.views.settings_dialog import SettingsDialog
import tkinter as tk

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
