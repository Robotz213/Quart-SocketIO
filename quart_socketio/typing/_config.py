from __future__ import annotations

from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Literal,
    TypedDict,
)

from quart import Quart

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable
    from configparser import RawConfigParser
    from logging import Logger
    from os import PathLike

    from quart import Quart
    from quart.json.provider import JSONProvider

    from quart_socketio.typing import (
        Any,
        AsyncMode,
        Channel,
        QueueClasses,
        SocketIo,
        Transports,
    )
    from quart_socketio.typing._types import LaunchMode


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


type Any = any

HTTPProtocolType = Literal["auto", "h11", "httptools"]
WSProtocolType = Literal["auto", "none", "websockets", "wsproto"]
LifespanType = Literal["auto", "on", "off"]
LoopSetupType = Literal["none", "auto", "asyncio", "uvloop"]
InterfaceType = Literal["auto", "asgi3", "asgi2", "wsgi"]


class RunKwargs(TypedDict):
    host: str
    port: int
    uds: str | None
    fd: int | None
    loop: LoopSetupType
    http: type[asyncio.Protocol] | HTTPProtocolType
    ws: type[asyncio.Protocol] | WSProtocolType
    ws_max_size: int
    ws_max_queue: int
    ws_ping_interval: float | None
    ws_ping_timeout: float | None
    ws_per_message_deflate: bool
    lifespan: LifespanType = "auto"
    env_file: str | PathLike[str] | None
    log_config: dict[str, Any] | str | RawConfigParser | IO[Any] | None
    log_level: str | int
    access_log: bool
    use_colors: bool
    interface: InterfaceType = "auto"
    reload: bool
    reload_dirs: list[str] | str
    reload_delay: float = 0.25
    reload_includes: list[str] | str
    reload_excludes: list[str] | str
    workers: int
    proxy_headers: bool
    server_header: bool
    date_header: bool
    forwarded_allow_ips: list[str] | str
    root_path: str = ""
    limit_concurrency: int
    limit_max_requests: int
    backlog: int = 2048
    timeout_keep_alive: int = 5
    timeout_notify: int = 30
    timeout_graceful_shutdown: int
    callback_notify: Callable[..., Awaitable[None]]
    ssl_keyfile: str | PathLike[str]
    ssl_certfile: str | PathLike[str]
    ssl_keyfile_password: str
    ssl_version: int
    ssl_cert_reqs: int
    ssl_ca_certs: str
    ssl_ciphers: str
    headers: list[tuple[str, str]]
    factory: bool
    h11_max_incomplete_event_size: int
