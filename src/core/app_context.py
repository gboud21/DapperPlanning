from typing import Any, Dict

class AppContext:
    """
    A lightweight Dependency Injection container for the DapperPlanning application.
    """
    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register(self, key: str, instance: Any) -> None:
        """Registers a service instance with a unique key."""
        self._services[key] = instance

    def resolve(self, key: str) -> Any:
        """Retrieves a service instance by key. Raises KeyError if not found."""
        if key not in self._services:
            raise KeyError(f"Service '{key}' not found in AppContext.")
        return self._services[key]
