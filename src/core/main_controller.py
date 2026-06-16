import os
import tkinter as tk
from tkinter import messagebox
from src.core.app_context import AppContext
from src.core.events import (
    EventDispatcher, UISyncRequestedEvent, UIExportCsvRequestedEvent, UIExportJsonRequestedEvent,
    UIImportCsvRequestedEvent, UIImportJsonRequestedEvent, ModelHierarchyUpdatedEvent,
    UIErrorNotificationEvent, UIThemeToggleRequestedEvent, AppThemeChangedEvent,
    ModelWorkspaceLoadedEvent, UIWindowStateChangedEvent, UIAppCloseRequestedEvent,
    UISaveWorkspaceRequestedEvent, UILogLevelChangedEvent, UIItemReparentRequestedEvent,
    UIStorySplitRequestedEvent, UILabelUpdateRequestedEvent, UIAppViewChangedEvent,
    UIUpdateCapacityMetricsRequestedEvent, UIPiPlannerTreeSelectionChangedEvent
)
from src.domain.workspace import Workspace
from src.domain.entities import Story
from src.domain.repositories import WorkspaceRepository
from src.features.agile_planning.tree_controller import TreeController
from src.features.agile_planning.editor_controller import EditorController
from src.core.menu_controller import MenuController
from src.features.integrations.integrations_controller import IntegrationsController
from src.features.settings.settings_controller import SettingsController
from src.features.pi_planning.pi_planning_controller import PIPlanningController
from src.utils.theme_manager import ThemeManager
from src.infrastructure.telemetry.logger import AppLogger, logger

class MainController:
    def __init__(self, context: AppContext):
        """
        Initializes the MainController and its sub-controllers.

        Args:
            context (AppContext): The application context for dependency injection.
        """
        self.context = context
        self.dispatcher: EventDispatcher = context.resolve('event_dispatcher')
        self.workspace: Workspace = context.resolve('workspace')
        self.repository: WorkspaceRepository = context.resolve('workspace_repository')
        self.root: tk.Tk = context.resolve('root_window')
        
        # Instantiate sub-controllers passing the context
        self.tree_controller = TreeController(context)
        self.editor_controller = EditorController(context)
        self.menu_controller = MenuController(context)
        self.integrations_controller = IntegrationsController(context)
        self.settings_controller = SettingsController(context)
        self.pi_planning_controller = PIPlanningController(context)
        
        self._subscribe_events()

        # Load initial theme state and notify view
        is_dark = ThemeManager.load_settings()
        self.dispatcher.dispatch(AppThemeChangedEvent(is_dark=is_dark))

        # Load window maximized state
        if ThemeManager.get_window_maximized():
            self._apply_maximized_state()

        # Load last workspace if it exists
        last_workspace = ThemeManager.get_last_workspace()
        if last_workspace and os.path.exists(last_workspace):
            self._load_initial_workspace()

    def _apply_maximized_state(self):
        """Applies the maximized state to the root window."""
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _load_initial_workspace(self):
        """Loads the workspace data using the repository at startup."""
        try:
            self.workspace = self.repository.load()
            # Update context to ensure other controllers can resolve the loaded workspace if needed
            self.context.register('workspace', self.workspace)
            
            # Notify views to update
            self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(root_items=self.workspace.get_epics()))
            if self.workspace.current_filepath:
                self.dispatcher.dispatch(ModelWorkspaceLoadedEvent(filepath=self.workspace.current_filepath))
        except Exception as e:
            # Silently fail initial load if file is corrupt, or notify via event
            print(f"Failed to load initial workspace: {e}")

    def _subscribe_events(self):
        """Subscribes to overarching application events."""
        self.dispatcher.subscribe(UISyncRequestedEvent, self.handle_sync)
        self.dispatcher.subscribe(UIWindowStateChangedEvent, self.handle_window_state_changed)
        self.dispatcher.subscribe(UIAppCloseRequestedEvent, self.handle_app_close)
        self.dispatcher.subscribe(UILogLevelChangedEvent, self.handle_log_level_changed)
        self.dispatcher.subscribe(ModelHierarchyUpdatedEvent, self.handle_model_updated)
        self.dispatcher.subscribe(UISaveWorkspaceRequestedEvent, self.handle_save_requested_log)
        self.dispatcher.subscribe(ModelWorkspaceLoadedEvent, self.handle_workspace_loaded)
        self.dispatcher.subscribe(UIItemReparentRequestedEvent, self.handle_reparent_requested)
        self.dispatcher.subscribe(UIStorySplitRequestedEvent, self.handle_split_requested)
        self.dispatcher.subscribe(UILabelUpdateRequestedEvent, self.handle_label_update)
        self.dispatcher.subscribe(UIAppViewChangedEvent, self.handle_view_changed)
        self.dispatcher.subscribe(UIUpdateCapacityMetricsRequestedEvent, self.handle_pi_capacity_update)

    def handle_pi_capacity_update(self, event: UIUpdateCapacityMetricsRequestedEvent):
        """Translates UI capacity updates into a transactional command."""
        from src.core.commands import UpdateMemberCapacityCommand
        self.context.resolve('command_bus').execute(UpdateMemberCapacityCommand(
            team_id=event.team_id,
            member_id=event.member_id,
            iteration_id=event.iteration_id,
            pto=event.pto,
            allocation_pct=event.allocation_pct,
            velocity_factor=event.velocity_factor
        ))

    def handle_view_changed(self, event: UIAppViewChangedEvent):
        """Safely unpacks current views and shifts layout content focus layers."""
        try:
            # Resolve main window out of context injection boundaries
            main_window = self.context.resolve('main_window')
        except KeyError:
            return

        # Unpack all initialized layout frame wrappers currently filling the slot canvas
        for name, view_frame in main_window.views.items():
            view_frame.pack_forget()
            
        # Remount target active layer container panel frame
        if event.view_name in main_window.views:
            main_window.views[event.view_name].pack(fill=tk.BOTH, expand=True)

    def handle_split_requested(self, event: UIStorySplitRequestedEvent):
        """Handles the request to split a story."""
        story = self.workspace._find_item_by_id(event.story_id)
        if not story or not isinstance(story, Story):
            return

        if story.weight <= 1.0:
            messagebox.showerror("Split Error", "Story weight is too low to split.")
            return

        from src.features.agile_planning.split_story_dialog import SplitStoryDialog
        dialog = SplitStoryDialog(self.root, story.title, story.weight)
        self.root.wait_window(dialog)
        
        if dialog.result:
            self.workspace.split_story(
                story_id=event.story_id,
                orig_new_weight=dialog.result["orig_weight"],
                clone_new_weight=dialog.result["clone_weight"],
                split_desc=dialog.result["reason"]
            )
            # Trigger save
            self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())

    def handle_reparent_requested(self, event: UIItemReparentRequestedEvent):
        """Orchestrates the workspace mutation and persistence for reparenting."""
        if event.item_type == "Feature":
            self.workspace.move_feature(event.item_id, event.new_parent_id)
        elif event.item_type == "Story":
            self.workspace.move_story(event.item_id, event.new_parent_id)
            
        # Re-dispatch hierarchy update to ensure UI reflects new order/parenting
        self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
            root_items=self.workspace.get_epics(),
            products=self.workspace.products
        ))
        # Trigger save to persist the move
        self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())

    def handle_label_update(self, event: UILabelUpdateRequestedEvent):
        """Processes label addition or removal, supporting recursive cascading."""
        legacy_enabled = self.settings_controller.settings.get('legacy_status_enabled', False)
        mappings = self.settings_controller.settings.get('status_label_mappings', {})

        if event.recursive:
            self.workspace.apply_label_recursively(
                item_id=event.item_id,
                item_type=event.item_type,
                label_name=event.label_name,
                add=event.add
            )
            # If recursive and legacy enabled, we'd need to update status for all children.
            # apply_label_recursively already dispatches HierarchyUpdated.
            # To be thorough, we should update status for all children too.
            if legacy_enabled:
                self._update_status_recursively(event.item_id, legacy_enabled, mappings)
        else:
            item = self.workspace._find_item_by_id(event.item_id)
            if item and hasattr(item, 'labels'):
                if event.add:
                    if event.label_name not in item.labels:
                        item.labels.append(event.label_name)
                        item.last_synced_at = None
                else:
                    if event.label_name in item.labels:
                        item.labels.remove(event.label_name)
                        item.last_synced_at = None
                
                if legacy_enabled and hasattr(item, 'status'):
                    new_status = self.workspace.resolve_legacy_status_from_labels(item.labels, legacy_enabled, mappings)
                    if new_status:
                        item.status = new_status

                self.dispatcher.dispatch(ModelHierarchyUpdatedEvent(
                    root_items=self.workspace.get_epics(),
                    products=self.workspace.products
                ))
        
        # Persist changes
        self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())

    def _update_status_recursively(self, item_id, legacy_enabled, mappings):
        item = self.workspace._find_item_by_id(item_id)
        if not item: return

        def _upd(obj):
            if hasattr(obj, 'labels') and hasattr(obj, 'status'):
                new_status = self.workspace.resolve_legacy_status_from_labels(obj.labels, legacy_enabled, mappings)
                if new_status:
                    obj.status = new_status
            
            if hasattr(obj, 'features'):
                for f in obj.features: _upd(f)
            if hasattr(obj, 'stories'):
                for s in obj.stories: _upd(s)
        
        _upd(item)

    def handle_workspace_loaded(self, event: ModelWorkspaceLoadedEvent):
        """Refreshes the workspace reference when a new one is loaded."""
        self.workspace = self.context.resolve('workspace')

    def handle_save_requested_log(self, event: UISaveWorkspaceRequestedEvent):
        """Logs telemetry when a save is triggered."""
        logger.info(f"Save requested. Workspace {id(self.workspace)} currently holds {len(self.workspace.get_epics())} root epics.")

    def handle_model_updated(self, event: ModelHierarchyUpdatedEvent):
        """Triggers auto-save if enabled when the model changes."""
        try:
            settings_manager = self.context.resolve('settings_manager')
            if settings_manager.get('auto_save', False):
                if self.workspace.has_unsaved_changes():
                    # Dispatch save request to be handled by MenuController
                    self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())
        except:
            # Fallback if settings_manager is not available
            pass

    def handle_log_level_changed(self, event: UILogLevelChangedEvent):
        """Updates the application logging level dynamically."""
        AppLogger.update_log_level(event.log_level)

    def handle_app_close(self, event: UIAppCloseRequestedEvent):
        """Intercepts application close to check for unsaved changes."""
        if not self.workspace.has_unsaved_changes():
            self.root.destroy()
            return

        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save before exiting?"
        )

        if response is True:  # Yes
            # Trigger save via MenuController's logic
            # Since events are dispatched and handled synchronously in the main thread:
            self.dispatcher.dispatch(UISaveWorkspaceRequestedEvent())
            # After save attempt, we check again if it's clean (save might have been cancelled in 'Save As' dialog)
            if not self.workspace.has_unsaved_changes():
                self.root.destroy()
        elif response is False:  # No
            self.root.destroy()
        # If response is None (Cancel), we do nothing, effectively aborting the close.

    def handle_sync(self, event: UISyncRequestedEvent):
        """Handles synchronization with external services (GitLab)."""
        if self.integrations_controller.validate_sync_readiness(self.workspace):
            # Proceed with sync logic
            pass

    def handle_window_state_changed(self, event: UIWindowStateChangedEvent):
        """Saves the window maximized state when it changes."""
        ThemeManager.set_window_maximized(event.is_maximized)
