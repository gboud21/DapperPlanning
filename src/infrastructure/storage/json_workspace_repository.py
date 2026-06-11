import os
import json
from src.domain.repositories import WorkspaceRepository
from src.domain.workspace import Workspace
from src.core.events import EventDispatcher
from src.infrastructure.storage.adapters import JSONAdapter
from src.infrastructure.telemetry.logger import logger

class JsonWorkspaceRepository(WorkspaceRepository):
    def __init__(self, file_path: str, dispatcher: EventDispatcher):
        """
        Initializes the JsonWorkspaceRepository.

        Args:
            file_path (str): The path to the JSON file for persistence.
            dispatcher (EventDispatcher): The event dispatcher needed to initialize Workspace.
        """
        self.file_path = file_path
        self.dispatcher = dispatcher

    def load(self) -> Workspace:
        """
        Loads the workspace from the JSON file. 
        If the file doesn't exist, returns a new empty Workspace.
        """
        workspace = Workspace(self.dispatcher)
        
        if os.path.exists(self.file_path):
            try:
                adapter = JSONAdapter()
                root_epics, active_product, products, members, deleted = adapter.import_data(self.file_path)
                
                workspace._epics = root_epics
                workspace.products = products
                workspace.members = {m.id: m for m in members}
                workspace.active_product_name = active_product
                workspace.deleted_remote_items = deleted
                workspace.current_filepath = self.file_path
                workspace.mark_as_clean()
            except Exception as e:
                # In case of error, we return an empty workspace but log the error
                print(f"Error loading workspace from {self.file_path}: {e}")
        
        return workspace

    def save(self, workspace: Workspace) -> None:
        """
        Saves the workspace to the JSON file.
        """
        try:
            adapter = JSONAdapter()
            epics = workspace.get_epics()
            logger.info(f"JsonWorkspaceRepository.save: Preparing to save {len(epics)} root epics (instance {id(workspace)}) to {self.file_path}")
            adapter.export_data(
                self.file_path,
                epics,
                active_product_name=workspace.active_product_name,
                products=workspace.products,
                members=workspace.get_members(),
                deleted_remote_items=workspace.deleted_remote_items
            )
            # Update workspace state after successful save
            workspace.current_filepath = self.file_path
            workspace.mark_as_clean()
        except Exception as e:
            raise IOError(f"Failed to save workspace to {self.file_path}: {e}")
