from __future__ import annotations  # noqa: D100

from typing import Any, Callable, Dict, List, Tuple

from quart import Quart

from quart_socketio._namespace import Namespace
from quart_socketio._types import ASyncServerType, TExceptionHandler


class Config:
    """Configuration for the Quart-SocketIO application."""

    handlers: List[Tuple[str, Callable[..., Any], str]] = []
    app: Quart = None
    host: str = "localhost"
    port: int = 5000
    debug: bool = False
    allow_unsafe_werkzeug: bool = False
    use_reloader: bool = False
    extra_files: List[str] = []
    reloader_options: Dict[str, Any] = {}
    server_options: Dict[str, Any] = {}
    launch_mode: str = "uvicorn"
    server: ASyncServerType = None
    namespace_handlers: List[Namespace] = []
    exception_handlers: Dict[str, TExceptionHandler] = {}
    default_exception_handler: TExceptionHandler = None
    manage_session: bool = True
    log_config: Dict[str, Any] = {}
    log_level: int = 20  # Default to logging.INFO

    def __init__(self, app: Quart = None, **kw: Any) -> None:
        """Initialize the configuration with the Quart application and additional parameters."""
        self.app = app
        self.update(**kw)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary with the configuration parameters."""
        kw = {item: getattr(self, item) for item in dir(Config) if not item.startswith("_") and item != "to_dict"}
        if self.app:
            kw["app"] = self.app
        return kw

    def update(self, **kwargs: Any) -> None:
        """Update the configuration with the provided keyword arguments."""
        for item in dir(Config):
            if not item.startswith("_") and item != "to_dict":
                setattr(self, item, kwargs.get(item, getattr(self, item, None)))
