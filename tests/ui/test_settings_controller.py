import pytest
from unittest.mock import MagicMock
from src.features.settings.settings_controller import SettingsController
from src.core.app_context import AppContext
from src.core.events import EventDispatcher, UISettingsSaveRequestedEvent, UILogLevelChangedEvent
from src.domain.workspace import Workspace

def test_settings_controller_dispatches_log_level_change(mocker, headless_tk):
    """Verifies that saving settings dispatches the correct logging level event."""
    # 1. Setup AppContext and mocks
    context = AppContext()
    
    mock_dispatcher = mocker.MagicMock(spec=EventDispatcher)
    mock_workspace = mocker.MagicMock(spec=Workspace)
    mock_workspace.get_epics.return_value = []
    
    context.register('event_dispatcher', mock_dispatcher)
    context.register('workspace', mock_workspace)
    context.register('root_window', headless_tk)
    
    # 2. Instantiate the controller
    # Note: Our SettingsController takes context in __init__.
    controller = SettingsController(context=context)
    
    # 3. Simulate user interaction
    # In this architecture, the View (SettingsDialog) dispatches a UISettingsSaveRequestedEvent.
    # The Controller handles it and dispatches the more granular UILogLevelChangedEvent.
    
    # We simulate the UI action by manually triggering the controller's handler.
    # This matches the Tier 3 objective of verifying controller dispatch logic.
    save_event = UISettingsSaveRequestedEvent(
        theme="dark",
        auto_save=True,
        log_level="DEBUG",
        show_status_in_tree=True,
        templates={},
        target_tool="GitLab",
        methodology="Scrum",
        hierarchy="Epic -> Feature -> Story",
        description_type="Heavyweight",
        include_out_of_scope=False,
        include_compliance=False,
        last_selected_item_type="Epic",
        selected_templates={}
    )
    
    # Patch ThemeManager to avoid real file I/O during test
    mocker.patch('src.utils.theme_manager.ThemeManager.get_general_settings', return_value={'log_level': 'INFO'})
    mocker.patch('src.utils.theme_manager.ThemeManager.save_general_settings')
    mocker.patch('src.utils.theme_manager.ThemeManager.apply_ttk_theme')

    # 4. Trigger the save method
    controller.handle_save_settings(save_event)
        
    # 5. Assert the correct event was dispatched into the system
    # We look for the UILogLevelChangedEvent specifically.
    dispatched_events = [call.args[0] for call in mock_dispatcher.dispatch.call_args_list]
    log_events = [e for e in dispatched_events if isinstance(e, UILogLevelChangedEvent)]
    
    assert len(log_events) >= 1, "UILogLevelChangedEvent was not dispatched!"
    assert log_events[-1].log_level == "DEBUG", f"Expected DEBUG, got {log_events[-1].log_level}"

def test_settings_dialog_save_dispatches_request(mocker, headless_tk):
    """Verifies that the SettingsDialog UI correctly dispatches the Save request event."""
    from src.features.settings.settings_dialog import SettingsDialog
    
    mock_dispatcher = mocker.MagicMock(spec=EventDispatcher)
    current_settings = {
        'theme': 'dark',
        'log_level': 'INFO',
        'auto_save': False,
        'templates': {}
    }
    
    # Instantiate the Dialog
    dialog = SettingsDialog(headless_tk, mock_dispatcher, current_settings)
    
    # Simulate user changing the log level in the combobox
    # As noted in research, the dialog uses combo_log_level directly.
    dialog.combo_log_level.set("DEBUG")
    
    # Simulate clicking the Save button
    dialog._on_save_clicked()
    
    # Verify UISettingsSaveRequestedEvent was dispatched with DEBUG
    dispatched_events = [call.args[0] for call in mock_dispatcher.dispatch.call_args_list]
    save_events = [e for e in dispatched_events if isinstance(e, UISettingsSaveRequestedEvent)]
    
    assert len(save_events) == 1
    assert save_events[0].log_level == "DEBUG"
    
    # Verify the dialog destroyed itself
    # (Since we are headless and using mocks, we just check if it's still alive)
    # dialog.winfo_exists() returns 0 if destroyed
    assert not dialog.winfo_exists()
