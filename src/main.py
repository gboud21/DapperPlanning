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

def main():
    """
    Main function to initialize and run the Dapper Planning application.
    """
    # 1. Initialize AppContext (DI Container)
    context = AppContext()

    # 2. Initialize Tkinter Root
    root = tk.Tk()
    root.title("Standardized Backlog Planning Tool")
    root.geometry("1000x700")
    root.minsize(800, 600)

    # Global style overrides for Combobox dropdowns to ensure black text readability
    root.option_add('*TCombobox*Listbox.foreground', 'black')
    root.option_add('*TCombobox*Listbox.background', 'white')
    root.option_add('*TCombobox*Listbox.selectForeground', 'white')
    root.option_add('*TCombobox*Listbox.selectBackground', '#0078d7')

    # 3. Initialize and Register Core Dependencies
    dispatcher = EventDispatcher(root)
    workspace = Workspace(dispatcher)
    
    context.register('event_dispatcher', dispatcher)
    context.register('workspace', workspace)
    context.register('root_window', root)

    # 4. Initialize View and Controller with AppContext
    view = MainWindow(root, context)
    controller = MainController(context)

    # 5. Start the Application
    root.mainloop()

if __name__ == "__main__":
    main()
