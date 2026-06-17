import pytest
from unittest.mock import MagicMock, patch
from src.features.integrations.conflict_resolution_modal import ConflictResolutionModal
from src.core.events import ModelHierarchyUpdatedEvent, UITreeFilterAppliedEvent
from src.domain.entities import Story, Team

class MockWorkspace:
    def __init__(self, items):
        self._items = items
        self.products = []
        self.shadow_hierarchy = {}
    def all_items_iterable(self):
        return self._items
    def get_epics(self):
        return []

@pytest.fixture
def setup_modal():
    parent = MagicMock()
    dispatcher = MagicMock()
    local_item = Story(id="s1", title="Local", description="", team=Team(name="A"), is_conflicted=True)
    remote_item = Story(id="s1", title="Remote", description="", team=Team(name="A"))
    workspace = MockWorkspace([local_item])
    
    # We need to mock Toplevel behavior and StringVars
    with patch('tkinter.StringVar'):
        with patch('tkinter.Toplevel.__init__', return_value=None):
            with patch('tkinter.Toplevel.title'):
                with patch('tkinter.Toplevel.geometry'):
                    with patch('tkinter.Toplevel.transient'):
                        with patch('tkinter.Toplevel.grab_set'):
                            with patch('tkinter.Toplevel.update_idletasks'):
                                with patch('tkinter.Toplevel.winfo_width', return_value=800):
                                    with patch('tkinter.Toplevel.winfo_height', return_value=600):
                                        with patch('tkinter.Toplevel.winfo_rootx', return_value=100):
                                            with patch('tkinter.Toplevel.winfo_rooty', return_value=100):
                                                with patch('tkinter.Toplevel.destroy'):
                                                    with patch('src.features.integrations.conflict_resolution_modal.ConflictResolutionModal._setup_ui'):
                                                        modal = ConflictResolutionModal(parent, dispatcher, local_item, remote_item, workspace)
                                    # Manually set some attributes that __init__ would set if it wasn't mocked
                                    modal.dispatcher = dispatcher
                                    modal.local_item = local_item
                                    modal.remote_item = remote_item
                                    modal.workspace = workspace
                                    # StringVars were mocked, so we need to set them on modal if we use them
                                    modal.chosen_title = MagicMock()
                                    modal.chosen_description = MagicMock()
                                    modal.chosen_weight = MagicMock()
                                    modal.chosen_status = MagicMock()
                                    modal.chosen_assignee = MagicMock()
                                    modal.chosen_iteration = MagicMock()
                                    modal.chosen_labels = MagicMock()
                                    modal.destroy = MagicMock()
                                    return modal, dispatcher, local_item, workspace

def test_resolution_with_remaining_conflicts(setup_modal):
    modal, dispatcher, local_item, workspace = setup_modal
    
    # Add another conflicted item
    other_item = Story(id="s2", title="Other", description="", team=Team(name="A"), is_conflicted=True)
    workspace._items.append(other_item)
    
    with patch('tkinter.messagebox.askokcancel', return_value=True):
        with patch('tkinter.messagebox.showinfo') as mock_info:
            modal._on_ok_clicked()
            
            assert local_item.is_conflicted is False
            assert other_item.is_conflicted is True
            
            # Should show remaining conflicts info
            args, kwargs = mock_info.call_args
            assert args[0] == "Conflicts Remaining"
            assert "There are 1 conflicts remaining" in args[1]
            assert kwargs['parent'] == modal
            
            # Should dispatch ModelHierarchyUpdatedEvent but NOT clear filter
            # Check dispatcher calls
            event_types = [type(call.args[0]) for call in dispatcher.dispatch.call_args_list]
            assert ModelHierarchyUpdatedEvent in event_types
            assert UITreeFilterAppliedEvent not in event_types

def test_resolution_with_no_remaining_conflicts(setup_modal):
    modal, dispatcher, local_item, workspace = setup_modal
    
    # Only s1 is conflicted (already in setup)
    
    with patch('tkinter.messagebox.askokcancel', return_value=True):
        with patch('tkinter.messagebox.showinfo') as mock_info:
            modal._on_ok_clicked()
            
            assert local_item.is_conflicted is False
            
            # Should show all resolved info
            args, kwargs = mock_info.call_args
            assert args[0] == "All Resolved"
            assert "All merge conflicts have been successfully resolved" in args[1]
            assert kwargs['parent'] == modal
            
            # Should dispatch UITreeFilterAppliedEvent to clear filter
            event_types = [type(call.args[0]) for call in dispatcher.dispatch.call_args_list]
            assert UITreeFilterAppliedEvent in event_types
            
            # Verify it's clearing the filter (query_string="")
            clear_event = next(c.args[0] for c in dispatcher.dispatch.call_args_list if isinstance(c.args[0], UITreeFilterAppliedEvent))
            assert clear_event.query_string == ""

def test_shadow_baseline_advanced(setup_modal):
    modal, dispatcher, local_item, workspace = setup_modal
    
    # Mock remote item attributes
    modal.remote_item.title = "Resolved Remote Title"
    modal.remote_item.description = "Resolved Remote Desc"
    
    with patch('tkinter.messagebox.askokcancel', return_value=True):
        with patch('tkinter.messagebox.showinfo'):
            modal._on_ok_clicked()
            
            # Verify shadow baseline for the item was updated to match remote
            assert local_item.id in workspace.shadow_hierarchy
            shadow_entry = workspace.shadow_hierarchy[local_item.id]
            assert shadow_entry['title'] == "Resolved Remote Title"
            assert shadow_entry['description'] == "Resolved Remote Desc"
