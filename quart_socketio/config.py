from collections import UserDict

from quart_socketio.typing._config import wrap_config

type Any = any


@wrap_config
class Config(UserDict):
    """Configuration for the Quart-SocketIO application."""

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(DEFAULTS)

        self.update(**kwargs)


DEFAULTS = {
    "app": None,
    "host": "localhost",
    "port": 5000,
    "debug": False,
    "use_reloader": False,
    "allow_unsafe_werkzeug": False,
    "handlers": [],
    "extra_files": [],
    "reloader_options": {},
    "server_options": {},
    "launch_mode": "uvicorn",
    "server": None,
    "namespace_handlers": [],
    "exception_handlers": {},
    "default_exception_handler": None,
    "manage_session": True,
    "log_config": None,
    "log_level": 0,
    "client_manager": None,
    "logger": False,
    "socketio_path": "/socket.io",
    "engineio_path": "/engine.io",
    "json": None,
    "async_handlers": True,
    "always_connect": False,
    "namespaces": "*",
    "async_mode": "asgi",
    "ping_interval": 25,
    "ping_timeout": 20,
    "max_http_buffer_size": 1000000,
    "allow_upgrades": True,
    "http_compression": True,
    "compression_threshold": 1024,
    "cookie": None,
    "cors_allowed_origins": "*",
    "cors_credentials": True,
    "monitor_clients": True,
    "transports": ["polling", "websocket"],
    "engineio_logger": False,
    "message_queue": None,
    "channel": "quart-socketio",
}
