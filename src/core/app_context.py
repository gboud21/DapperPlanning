from typing import Any, Dict, List

class AppContext:
    """
    A lightweight Dependency Injection container for the DapperPlanning application.
    Supports service registration and FeatureModule orchestration.
    """
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._features: List[Any] = [] # List[FeatureModule] - avoided type hint to prevent circular import

    def register(self, key: str, instance: Any) -> None:
        """Registers a service instance with a unique key."""
        self._services[key] = instance

    def resolve(self, key: str) -> Any:
        """Retrieves a service instance by key. Raises KeyError if not found."""
        if key not in self._services:
            raise KeyError(f"Service '{key}' not found in AppContext.")
        return self._services[key]

    def register_feature(self, feature: Any) -> None:
        """Registers a FeatureModule instance."""
        self._features.append(feature)

    def get_features(self) -> List[Any]:
        """Returns all registered FeatureModule instances."""
        return self._features
