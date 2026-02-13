"""Lazy loading utilities for deferred registry initialization."""


class LazyRegistry:
    """Proxy that defers Registry instantiation until first attribute access."""

    def __init__(self, factory_func):
        """
        Args:
            factory_func: Callable that returns the actual Registry instance.
        """
        self._factory = factory_func
        self._instance = None

    def _ensure_loaded(self):
        """Instantiate the registry on first access."""
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def __getattr__(self, name):
        """Delegate all attribute access to the actual registry."""
        return getattr(self._ensure_loaded(), name)

    def __iter__(self):
        """Delegate iteration to the actual registry."""
        return iter(self._ensure_loaded())

    def __len__(self):
        """Delegate len() to the actual registry."""
        return len(self._ensure_loaded())

    def __repr__(self):
        """Show whether the registry is loaded."""
        if self._instance is None:
            return "<LazyRegistry(not loaded)>"
        return repr(self._instance)
