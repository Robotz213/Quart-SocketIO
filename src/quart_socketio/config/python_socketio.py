import logging  # noqa: D100
from typing import Any, Dict, List, Optional, Union

from quart_socketio._types import CustomJsonClass, TQueueClasses


class AsyncSocketIOConfig:
    """Configuration for the Quart-SocketIO server.

    :param client_manager: The client manager instance that will manage the
                           client list. When this is omitted, the client list
                           is stored in an in-memory structure, so the use of
                           multiple connected servers is not possible.


    :param logger: To enable logging set to ``True`` or pass a logger object to
                   use. To disable logging set to ``False``. Note that fatal
                   errors are logged even when ``logger`` is ``False``.
    :param json: An alternative json module to use for encoding and decoding
                 packets. Custom json modules must have ``dumps`` and ``loads``
                 functions that are compatible with the standard library
                 versions.
    :param async_handlers: If set to ``True``, event handlers for a client are
                           executed in separate threads. To run handlers for a
                           client synchronously, set to ``False``. The default
                           is ``True``.
    :param always_connect: When set to ``False``, new connections are
                           provisory until the connect handler returns
                           something other than ``False``, at which point they
                           are accepted. When set to ``True``, connections are
                           immediately accepted, and then if the connect
                           handler returns ``False`` a disconnect is issued.
                           Set to ``True`` if you need to emit events from the
                           connect handler and your client is confused when it
                           receives events before the connection acceptance.
                           In any other case use the default of ``False``.
    :param namespaces: a list of namespaces that are accepted, in addition to
                       any namespaces for which handlers have been defined. The
                       default is `['/']`, which always accepts connections to
                       the default namespace. Set to `'*'` to accept all
                       namespaces.
    :param kwargs: Connection parameters for the underlying Engine.IO server.

    :param ping_interval: The interval in seconds at which the server pings
                          the client. The default is 25 seconds. For advanced
                          control, a two element tuple can be given, where
                          the first number is the ping interval and the second
                          is a grace period added by the server.
    :param ping_timeout: The time in seconds that the client waits for the
                         server to respond before disconnecting. The default
                         is 20 seconds.
    :param max_http_buffer_size: The maximum size that is accepted for incoming
                                 messages.  The default is 1,000,000 bytes. In
                                 spite of its name, the value set in this
                                 argument is enforced for HTTP long-polling and
                                 WebSocket connections.
    :param allow_upgrades: Whether to allow transport upgrades or not. The
                           default is ``True``.
    :param http_compression: Whether to compress packages when using the
                             polling transport. The default is ``True``.
    :param compression_threshold: Only compress messages when their byte size
                                  is greater than this value. The default is
                                  1024 bytes.
    :param cookie: If set to a string, it is the name of the HTTP cookie the
                   server sends back to the client containing the client
                   session id. If set to a dictionary, the ``'name'`` key
                   contains the cookie name and other keys define cookie
                   attributes, where the value of each attribute can be a
                   string, a callable with no arguments, or a boolean. If set
                   to ``None`` (the default), a cookie is not sent to the
                   client.
    :param cors_allowed_origins: Origin or list of origins that are allowed to
                                 connect to this server. Only the same origin
                                 is allowed by default. Set this argument to
                                 ``'*'`` to allow all origins, or to ``[]`` to
                                 disable CORS handling.
    :param cors_credentials: Whether credentials (cookies, authentication) are
                             allowed in requests to this server. The default is
                             ``True``.
    :param monitor_clients: If set to ``True``, a background task will ensure
                            inactive clients are closed. Set to ``False`` to
                            disable the monitoring task (not recommended). The
                            default is ``True``.
    :param transports: The list of allowed transports. Valid transports
                       are ``'polling'`` and ``'websocket'``. Defaults to
                       ``['polling', 'websocket']``.
    :param engineio_logger: To enable Engine.IO logging set to ``True`` or pass
                            a logger object to use. To disable logging set to
                            ``False``. The default is ``False``. Note that
                            fatal errors are logged even when
                            ``engineio_logger`` is ``False``.


    """

    client_manager: TQueueClasses = None
    logger: bool = False
    socketio_path: str = "/socket.io"
    engineio_path: str = "/engine.io"
    json: CustomJsonClass = None
    async_handlers: bool = True
    always_connect: bool = False
    namespaces: Union[str, List[str]] = "*"
    async_mode: Optional[str] = "asgi"
    ping_interval: Union[int, tuple] = 25
    ping_timeout: int = 20
    max_http_buffer_size: int = 1000000
    allow_upgrades: bool = True
    http_compression: bool = True
    compression_threshold: int = 1024
    cookie: Optional[Union[str, Dict[str, Any]]] = None
    cors_allowed_origins: Union[str, List[str]] = "*"
    cors_credentials: bool = True
    monitor_clients: bool = True
    transports: List[str] = ["polling", "websocket"]
    engineio_logger: Union[bool, logging.Logger] = False
    message_queue: Optional[str] = None
    channel: str = "quart-socketio"

    def __init__(self, **kw: Any) -> None:
        """Initialize the configuration with the provided keyword arguments."""
        self.update(**kw)

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
        for item in dir(AsyncSocketIOConfig):
            if not item.startswith("_") and item != "to_dict":
                setattr(self, item, kwargs.get(item, getattr(self, item, None)))
