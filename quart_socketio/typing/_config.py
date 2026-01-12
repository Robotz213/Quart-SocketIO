from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from logging import Logger

    from quart import Quart
    from quart.json.provider import JSONProvider

    from quart_socketio.typing import Any, AsyncMode, QueueClasses, Transports
    from quart_socketio.typing._classes import SocketIo
    from quart_socketio.typing._types import LaunchMode

    from ._types import Channel


class Config(TypedDict):
    handlers: object
    app: Quart
    host: str
    port: int
    debug: bool
    use_reloader: bool
    allow_unsafe_werkzeug: bool
    extra_files: list[str]
    reloader_options: dict[str, Any]
    server_options: dict[str, Any]
    launch_mode: LaunchMode
    server: SocketIo
    namespace_handlers: list[Any]
    exception_handlers: dict[str, Any]
    default_exception_handler: Any
    manage_session: bool
    log_config: dict[str, Any]
    log_level: int
    client_manager: QueueClasses
    logger: bool
    socketio_path: Literal["/socket.io"]
    engineio_path: Literal["/engine.io"]
    json: JSONProvider
    async_handlers: bool
    always_connect: bool
    namespaces: str | list[str]
    async_mode: AsyncMode = "asgi"
    ping_interval: int | tuple
    ping_timeout: int
    max_http_buffer_size: int
    allow_upgrades: bool
    http_compression: bool
    compression_threshold: int
    cookie: str | dict[str, Any]
    cors_allowed_origins: str | list[str]
    cors_credentials: bool
    monitor_clients: bool
    transports: Transports
    engineio_logger: bool | Logger
    message_queue: str
    channel: Channel


def wrap_config[T](cls: T) -> type[Config]:

    return cls
