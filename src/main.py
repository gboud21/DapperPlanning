import tkinter as tk
import sys
import os

# Ensure the root of the project is in the path to allow imports from 'src'
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.core.app_context import AppContext
from src.core.events import EventDispatcher
from src.domain.workspace import Workspace
from src.core.main_window import MainWindow
from src.core.main_controller import MainController
from src.infrastructure.storage.settings_manager import SettingsManager

def main():
    """
    Main function to initialize and run the Dapper Planning application.
    """
    # 1. Initialize AppContext (DI Container)
    context = AppContext()

    # 2. Initialize Infrastructure
    settings_manager = SettingsManager()
    context.register('settings_manager', settings_manager)

    # 3. Initialize Tkinter Root
    root = tk.Tk()
    root.title("Standardized Backlog Planning Tool")
    root.geometry("1000x700")
    root.minsize(800, 600)

    # Global style overrides for Combobox dropdowns to ensure black text readability
    root.option_add('*TCombobox*Listbox.foreground', 'black')
    root.option_add('*TCombobox*Listbox.background', 'white')
    root.option_add('*TCombobox*Listbox.selectForeground', 'white')
    root.option_add('*TCombobox*Listbox.selectBackground', '#0078d7')

    # 4. Initialize and Register Core Dependencies
    dispatcher = EventDispatcher(root)
    workspace = Workspace(dispatcher)
    
    # Initialize Command Bus
    from src.core.command_bus import CommandBus
    command_bus = CommandBus()
    
    # Initialize Repository
    from src.infrastructure.storage.json_workspace_repository import JsonWorkspaceRepository
    from src.utils.theme_manager import ThemeManager
    from src.utils.paths import get_output_dir
    
    last_workspace_path = ThemeManager.get_last_workspace() or str(get_output_dir() / 'workspace.json')
    repository = JsonWorkspaceRepository(last_workspace_path, dispatcher)
    
    context.register('event_dispatcher', dispatcher)
    context.register('command_bus', command_bus)
    context.register('workspace', workspace)
    context.register('workspace_repository', repository)
    context.register('root_window', root)

    # 5. Initialize View and Controller with AppContext
    view = MainWindow(root, context)
    controller = MainController(context)

    # 6. Start the Application
    root.mainloop()

if __name__ == "__main__":
    main()
