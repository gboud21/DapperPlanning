import pytest
from unittest.mock import MagicMock
from src.features.integrations.integrations_controller import IntegrationsController
from src.core.app_context import AppContext
from src.core.events import EventDispatcher, UISyncMembersRequestedEvent
from src.domain.workspace import Workspace
from src.infrastructure.storage.settings_manager import SettingsManager
from src.domain.entities import Product

def test_integrations_controller_handles_sync_members(mocker, headless_tk):
    """Verifies that IntegrationsController initiates member sync on event."""
    context = AppContext()
    
    mock_dispatcher = mocker.MagicMock(spec=EventDispatcher)
    mock_workspace = mocker.MagicMock(spec=Workspace)
    mock_settings = mocker.MagicMock(spec=SettingsManager)
    
    # Configure Workspace mock
    mock_workspace.active_product_name = "DapperPlanning"
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = 888
    product.gitlab_group_id = 999
    mock_workspace.products = [product]
    
    # Configure Settings mock
    mock_settings.get.side_effect = lambda key, default=None: {
        'auth_url': 'https://gitlab.com',
        'auth_pat': 'fake_token',
        'epic_group_id': '999'
    }.get(key, default)
    
    context.register('event_dispatcher', mock_dispatcher)
    context.register('workspace', mock_workspace)
    context.register('settings_manager', mock_settings)
    context.register('root_window', headless_tk)
    context.register('command_bus', MagicMock())
    
    controller = IntegrationsController(context)
    
    # Mock SyncWorker to avoid thread spawning
    mock_worker = mocker.patch('src.features.integrations.integrations_controller.SyncWorker')
    
    # Trigger the event handler
    event = UISyncMembersRequestedEvent()
    controller.handle_sync_members(event)
    
    # Assert worker was initialized with 'members' type and started
    mock_worker.assert_called_once()
    args, kwargs = mock_worker.call_args
    assert kwargs.get('sync_type') == 'members'
    mock_worker.return_value.start.assert_called_once()
    
    # Assert progress modal was created
    assert controller.progress_modal is not None

def test_integrations_controller_handles_dry_push_command(mocker, headless_tk):
    """Verifies that IntegrationsController starts a dry-push sync worker, even when unresolved conflicts exist."""
    context = AppContext()
    
    mock_dispatcher = mocker.MagicMock(spec=EventDispatcher)
    mock_workspace = mocker.MagicMock(spec=Workspace)
    mock_settings = mocker.MagicMock(spec=SettingsManager)
    
    # Configure Workspace mock with a conflicted item
    mock_workspace.active_product_name = "DapperPlanning"
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = 888
    product.gitlab_group_id = 999
    mock_workspace.products = [product]
    
    conflicted_item = MagicMock()
    conflicted_item.is_conflicted = True
    mock_workspace.all_items_iterable.return_value = [conflicted_item]
    
    # Configure Settings mock
    mock_settings.get.side_effect = lambda key, default=None: {
        'auth_url': 'https://gitlab.com',
        'auth_pat': 'fake_token',
        'epic_group_id': '999'
    }.get(key, default)
    
    context.register('event_dispatcher', mock_dispatcher)
    context.register('workspace', mock_workspace)
    context.register('settings_manager', mock_settings)
    context.register('root_window', headless_tk)
    context.register('command_bus', MagicMock())
    
    controller = IntegrationsController(context)
    
    # Mock SyncWorker to avoid thread spawning
    mock_worker = mocker.patch('src.features.integrations.integrations_controller.SyncWorker')
    
    # 1. Test push command is blocked by conflicts
    mocker.patch('tkinter.messagebox.showerror')
    from src.core.commands import SyncWithGitLabCommand
    
    push_command = SyncWithGitLabCommand(sync_type='push')
    controller.handle_sync_with_gitlab(push_command)
    
    import tkinter.messagebox
    tkinter.messagebox.showerror.assert_called_once()
    mock_worker.assert_not_called()
    
    # Reset mocks
    tkinter.messagebox.showerror.reset_mock()
    mock_worker.reset_mock()
    
    # 2. Test dry-push command is NOT blocked by conflicts
    dry_push_command = SyncWithGitLabCommand(sync_type='dry-push')
    controller.handle_sync_with_gitlab(dry_push_command)
    
    tkinter.messagebox.showerror.assert_not_called()
    mock_worker.assert_called_once()
    args, kwargs = mock_worker.call_args
    assert kwargs.get('sync_type') == 'dry-push'
    mock_worker.return_value.start.assert_called_once()

def test_integrations_controller_handles_dry_push_completed_event(mocker, headless_tk):
    """Verifies that IntegrationsController shows the DryPushSummaryModal on ModelDryPushCompletedEvent."""
    context = AppContext()
    
    mock_dispatcher = mocker.MagicMock(spec=EventDispatcher)
    mock_workspace = mocker.MagicMock(spec=Workspace)
    mock_settings = mocker.MagicMock(spec=SettingsManager)
    
    context.register('event_dispatcher', mock_dispatcher)
    context.register('workspace', mock_workspace)
    context.register('settings_manager', mock_settings)
    context.register('root_window', headless_tk)
    context.register('command_bus', MagicMock())
    
    controller = IntegrationsController(context)
    
    # Mock DryPushSummaryModal
    mock_modal = mocker.patch('src.features.integrations.integrations_controller.DryPushSummaryModal')
    
    # Dispatch event
    from src.core.events import ModelDryPushCompletedEvent
    event = ModelDryPushCompletedEvent(creations=1, updates=2, conflicts=0, deletions=1, report_path="/path/to/report")
    
    controller.handle_dry_push_completed(event)
    
    mock_modal.assert_called_once_with(
        headless_tk,
        1, 2, 0, 1,
        "/path/to/report"
    )

