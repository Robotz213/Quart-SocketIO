from dataclasses import dataclass, field  # noqa: D100
from typing import Any, Callable, Dict, List, Tuple

from quart import Quart

from quart_socketio._namespace import Namespace
from quart_socketio._types import ASyncServerType, TExceptionHandler


@dataclass(match_args=False, eq=False, init=False)
class Config:
    """Configuration for the Quart-SocketIO application."""

    handlers: List[Tuple[str, Callable[..., Any], str]] = field(default_factory=list)
    app: Quart = None
    debug: bool = False
    allow_unsafe_werkzeug: bool = False
    use_reloader: bool = False
    extra_files: List[str] = field(default_factory=list)
    reloader_options: Dict[str, Any] = field(default_factory=dict)
    server_options: Dict[str, Any] = field(default_factory=dict)
    launch_mode: str = "uvicorn"
    server: ASyncServerType = None
    namespace_handlers: List[Namespace] = field(default_factory=list)
    exception_handlers: Dict[str, TExceptionHandler] = field(default_factory=dict)
    default_exception_handler: TExceptionHandler = None
    manage_session: bool = True

    def __init__(self, app: Quart = None, **kw: Any) -> None:
        """Initialize the configuration with the Quart application and additional parameters."""
        self.app = app
        self.update(**kw)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary with the configuration parameters."""
        kw = {item: getattr(self, item) for item in dir(Config) if not item.startswith("_") and item != "to_dict"}

        return kw

    def update(self, **kwargs: Any) -> None:
        """Update the configuration with the provided keyword arguments."""
        for item in dir(Config):
            if not item.startswith("_") and item != "to_dict":
                setattr(self, item, kwargs.get(item, getattr(self, item, None)))
