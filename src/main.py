import tkinter as tk
import sys
import os

# Ensure the root of the project is in the path to allow imports from 'src'
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.events import EventDispatcher
from src.models.workspace import Workspace
from src.views.main_window import MainWindow
from src.controllers.main_controller import MainController

def main():
    """
    Main function to initialize and run the Dapper Planning application.
    """
    # 1. Initialize Tkinter Root
    root = tk.Tk()
    root.title("Standardized Backlog Planning Tool")
    root.geometry("1000x700")

    # 2. Initialize the Event Dispatcher (Local Scope)
    dispatcher = EventDispatcher(root)

    # 3. Initialize Model, View, and Controller with Dependency Injection
    workspace = Workspace(dispatcher)
    controller = MainController(dispatcher, workspace)
    view = MainWindow(root, dispatcher)

    # 4. Start the Application
    root.mainloop()

if __name__ == "__main__":
    main()