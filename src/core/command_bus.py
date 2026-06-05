from typing import Dict, Type, Callable
from src.core.commands import Command

class CommandBus:
    """
    A central bus for routing Commands to specific handlers.
    Enforces a strict 1-to-1 mapping between Command types and Handlers.
    """
    def __init__(self):
        self._handlers: Dict[Type[Command], Callable] = {}

    def register(self, command_type: Type[Command], handler: Callable[[Command], None]) -> None:
        """
        Registers a single handler for a specific command type.
        
        Args:
            command_type (Type[Command]): The class of the command to handle.
            handler (Callable): The function or method to execute when the command is received.
            
        Raises:
            ValueError: If a handler is already registered for this command type.
        """
        if command_type in self._handlers:
            raise ValueError(f"Handler already registered for command type: {command_type.__name__}")
        self._handlers[command_type] = handler

    def execute(self, command: Command) -> None:
        """
        Routes a command to its registered handler and executes it.
        
        Args:
            command (Command): The command instance to execute.
            
        Raises:
            KeyError: If no handler is registered for the given command type.
        """
        command_type = type(command)
        if command_type not in self._handlers:
            raise KeyError(f"No handler registered for command: {command_type.__name__}")
        
        handler = self._handlers[command_type]
        handler(command)
