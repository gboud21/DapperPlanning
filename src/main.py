import tkinter as tk
from src.events import EventDispatcher
from src.models.workspace import Workspace
from src.views.main_window import MainWindow
from src.controllers.main_controller import MainController

def main():
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