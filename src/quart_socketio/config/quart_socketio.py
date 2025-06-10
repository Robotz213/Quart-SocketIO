from dataclasses import dataclass  # noqa: D100
from typing import Any, Callable, Dict, List, Tuple

from quart import Quart

from quart_socketio._namespace import Namespace
from quart_socketio._types import ASyncServerType, TExceptionHandler
from quart_socketio.config.python_socketio import AsyncSocketIOConfig


@dataclass
class Config:
    """Configuration for the Quart-SocketIO application."""

    handlers: List[Tuple[str, Callable[..., Any], str]] = []
    app: Quart = None
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

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary with the configuration parameters."""
        kw = {
            item: getattr(self, item)
            for item in dir(AsyncSocketIOConfig)
            if not item.startswith("_") and item != "to_dict"
        }

        return kw

    def update(self, **kwargs: Any) -> None:
        """Update the configuration with the provided keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
