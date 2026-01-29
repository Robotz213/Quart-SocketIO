from __future__ import annotations

from asyncio import Event
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Unpack,
    overload,
)

import quart
import socketio
from quart import Quart, Request, Websocket, session
from quart import json as quart_json
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from werkzeug.datastructures.headers import Headers

from quart_socketio.common.exceptions import (
    raise_runtime_error,
    raise_value_error,
)
from quart_socketio.config import Config
from quart_socketio.middleare import QuartSocketIOMiddleware as Middleware
from quart_socketio.namespace import Namespace
from quart_socketio.test_client import SocketIOTestClient

from ._manager import _ManagedSession

if TYPE_CHECKING:
    from logging import Logger

    from uvicorn import Server

    from quart_socketio.typing import (
        Any,
        AsyncMode,
        Channel,
        HypercornServer,
        Kw,
        QueueClasses,
        QueueClassMap,
        SocketIo,
        Transports,
    )
    from quart_socketio.typing._quart import CustomJsonClass

    from .typing._config import RunKwargs

type Any = any


class Controller:
    server: SocketIo = None
    asgi_server: Server | HypercornServer = None
    shutdown_event = Event()
    config: Config = None
    sockio_mw: Middleware = None

    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(
        self,
        *,
        handlers: object,
        app: Quart,
        host: str,
        port: int,
        debug: bool,
        use_reloader: bool,
        allow_unsafe_werkzeug: bool,
        extra_files: list[str],
        reloader_options: dict[str, Any],
        server_options: dict[str, Any],
        server: SocketIo,
        namespace_handlers: list[Any],
        exception_handlers: dict[str, Any],
        default_exception_handler: Any,
        manage_session: bool,
        log_config: dict[str, Any],
        log_level: int,
        client_manager: QueueClasses,
        logger: bool,
        socketio_path: Literal["/socket.io"],
        engineio_path: Literal["/engine.io"],
        json: CustomJsonClass,
        async_handlers: bool,
        always_connect: bool,
        namespaces: str | list[str],
        ping_interval: int | tuple,
        ping_timeout: int,
        max_http_buffer_size: int,
        allow_upgrades: bool,
        http_compression: bool,
        compression_threshold: int,
        cookie: str | dict[str, Any],
        cors_allowed_origins: str | list[str],
        cors_credentials: bool,
        monitor_clients: bool,
        transports: Transports,
        engineio_logger: bool | Logger,
        message_queue: str,
        channel: Channel,
        async_mode: AsyncMode = "asgi",
    ) -> None: ...

    def __init__(
        self,
        **kwargs: Kw,
    ) -> None:
        app: Quart = kwargs.get("app")
        self.config = Config(app=app, **kwargs)
        self.server_options = self.config
        if app is not None or self.config.get("message_queue"):
            self.init_app(app=app, **kwargs)

    def configure_server(self) -> socketio.AsyncServer:
        server = socketio.AsyncServer(**self.config)
        for handler in self.config["handlers"]:
            server.on(handler[0], handler[1], namespace=handler[2])

        for namespace_handler in self.config["namespace_handlers"]:
            server.register_namespace(namespace_handler)

        server._trigger_event = self._trigger_event  # noqa: SLF001
        return server

    def init_app(
        self,
        app: Quart,
        **kwargs: Kw,
    ) -> None:
        """Initialize the SocketIO extension for the given Quart application.

        :param app: The Quart application instance to initialize with SocketIO.
        :param kwargs: Additional keyword arguments for server configuration.
        """
        self.app = app or self.config["app"]
        self.config.update(app=app)
        self.config.update(**kwargs)

        if not hasattr(app, "extensions"):
            app.extensions = {}  # pragma: no cover

        if "client_manager" not in kwargs:
            self.client_manager(app)

        if (
            self.server_options["json"]
            and self.server_options["json"] == quart_json
        ):
            self.json_setting(app)

        socketio_path = self.server_options["socketio_path"]
        self.server = self.configure_server()

        kw = {
            "socketio_app": self.server,
            "quart_app": app,
            "socketio_path": socketio_path,
        }
        self.sockio_mw = Middleware(**kw)
        app.asgi_app = ProxyHeadersMiddleware(app.asgi_app)
        app.asgi_app = self.sockio_mw
        app.extensions["socketio"] = self

    def run(
        self,
        app: Quart = None,
        **kwargs: Unpack[RunKwargs],
    ) -> None:
        self.config.update(**kwargs)
        self.server_options = self.config

        app = self.config["app"]

        if not app:
            raise_value_error(
                "Quart application instance is required to run the server.",
            )

        if self.config["extra_files"]:
            self.config["reloader_options"]["extra_files"] = self.config[
                "extra_files"
            ]

        app.debug = self.config["debug"]

        from quart_socketio._uvicorn import run_uvicorn

        run_uvicorn(**self.config)

    def client_manager(self, app: Quart) -> None:
        url = self.server_options["message_queue"]
        channel: str = self.server_options["channel"]
        write_only: bool = app is None
        if url:
            queue_class = socketio.KombuManager
            queue_class_map: QueueClassMap = {
                ("redis://", "rediss://"): socketio.AsyncRedisManager,
                ("kafka://",): socketio.KafkaManager,
                ("zmq",): socketio.ZmqManager,
            }
            for prefixes, cls in queue_class_map.items():
                if url.startswith(prefixes):
                    queue_class = cls
                    break

            queue = queue_class(url, channel=channel, write_only=write_only)
            self.server_options["client_manager"] = queue

    def json_setting(self, app: Quart) -> None:
        """Json settings for the Quart-SocketIO server.

        Quart's json module is tricky to use because its output
        changes when it is invoked inside or outside the app context
        so here to prevent any ambiguities we replace it with wrappers
        that ensure that the app context is always present

        Arguments:
            app (Quart): The Quart application instance to use for the context.

        """

        class QuartSafeJson:
            @staticmethod
            async def dumps(
                *args: str | int | bool,
                **kwargs: str | int | bool,
            ) -> str:
                async with app.app_context():
                    return quart_json.dumps(*args, **kwargs)

            @staticmethod
            async def loads(
                *args: str | int | bool,
                **kwargs: str | int | bool,
            ) -> dict[str, Any | int | bool]:
                async with app.app_context():
                    return quart_json.loads(*args, **kwargs)

        self.config["json"] = QuartSafeJson

    @classmethod
    def load_headers(cls, environ: dict[str, Any]) -> Headers:  # noqa: C901
        """Load headers from the ASGI scope."""
        headers = Headers()

        io_headers: list[tuple[Any, Any]] = environ["asgi.scope"]["headers"]
        for item1, item2 in io_headers:
            header_key = item1
            header_value = item2
            if isinstance(header_key, bytes):
                header_key = header_key.decode("utf-8")

            if isinstance(header_value, bytes):
                header_value = header_value.decode("utf-8")

            headers.add(header_key.title(), header_value)

        for key, value in list(environ.items()):
            if isinstance(value, Callable) or (
                key == "wsgi.input" or key == "asgi.input"
            ):
                continue

            header_name = key
            if key.startswith("HTTP_"):
                header_name = key.split("_")[-1].title()
                header_value = value
                if isinstance(header_value, bytes):
                    header_value = header_value.decode("utf-8")

            elif isinstance(value, dict):
                for k, v in value.items():
                    v_decoded = v
                    if isinstance(v, str):
                        try:
                            if isinstance(v, bytes):
                                v_decoded = v.decode("utf-8")

                        except UnicodeDecodeError:
                            # If decoding fails, keep it as bytes
                            pass
                        headers.add(k.title(), v_decoded)

            if key.startswith("HTTP_"):
                headers.add(header_name, header_value)
            else:
                headers.add(header_name, value)

        return headers

    async def handle_session(
        self,
        environ: dict[str, str | dict[str, Any]],
    ) -> None:
        """Handle user sessions for Socket.IO events.

        This method is called to manage user sessions when the Socket.IO server
        is initialized with `manage_session=True`. It ensures that the session
        is properly saved and restored during Socket.IO events.
        :param environ: The ASGI environment dictionary.
        """
        app = self.config["app"]

        session_obj: _ManagedSession | Any = (
            environ.setdefault("saved_session", _ManagedSession(session))
            if self.config["manage_session"]
            else session._get_current_object()  # noqa: SLF001
        )
        ctx = (
            quart.globals.websocket_ctx._get_current_object()  # noqa: SLF001
            if hasattr(quart, "globals")
            and hasattr(quart.globals, "websocket_ctx")
            else quart._websocket_ctx_stack.top  # noqa: SLF001
        )
        if self.config["manage_session"]:
            ctx.session = session_obj

        # when Quart is managing the user session, it needs to save it
        if not hasattr(session_obj, "modified") or session_obj.modified:
            resp = app.response_class()
            app.session_interface.save_session(app, session_obj, resp)

    async def make_request(
        self,
        environ: dict[str, Any | dict[str, Any]],
        sid: str,
        namespace: str,
    ) -> Request:

        request = Request(
            method=environ["REQUEST_METHOD"],
            scheme=environ["asgi.scope"].get("scheme", "http"),
            path=environ["PATH_INFO"],
            query_string=environ["asgi.scope"]["query_string"],
            headers=self.load_headers(environ),
            root_path=environ["asgi.scope"].get("root_path", ""),
            http_version=environ["SERVER_PROTOCOL"],
            scope=environ["asgi.scope"],
            send_push_promise=self.send_push_promise,
        )

        request.sid = sid
        request.namespace = namespace

        return request

    async def make_websocket(self, **kwargs: Any) -> Request:
        kwargs = kwargs or {}
        environ = self.server.get_environ(
            kwargs["sid"],
            namespace=kwargs["namespace"],
        )
        websock = Websocket(
            path=environ["PATH_INFO"],
            query_string=environ["asgi.scope"]["query_string"],
            scheme=environ["asgi.scope"].get("scheme", "http"),
            headers=self.load_headers(environ),
            root_path=environ["asgi.scope"].get("root_path", ""),
            http_version=environ["SERVER_PROTOCOL"],
            receive=environ["asgi.receive"],
            send=environ["asgi.send"],
            subprotocols=environ["asgi.scope"].get("subprotocols", []),
            accept=environ["asgi.scope"].get("accept"),
            close=environ["asgi.scope"].get("close"),
            scope=environ["asgi.scope"],
        )
        websock.sid = kwargs.get("sid", None)

        return websock

    async def register_handler(
        self,
        handler_args: tuple[str, Callable[..., Any], str],
    ) -> None:

        event, handler, namespace = handler_args
        self.on(event=event, namespace=namespace)(handler)

    def test_client(
        self,
        app: Quart,
        namespace: str,
        query_string: str,
        headers: dict[str, str],
        auth: dict[str, Any],
        quart_test_client: Any = None,
    ) -> SocketIOTestClient:

        return SocketIOTestClient(
            app,
            self,
            namespace=namespace,
            query_string=query_string,
            headers=headers,
            auth=auth,
            quart_test_client=quart_test_client,
        )

    def register_namespace(self, namespace_handler: Namespace) -> None:
        """Register a namespace handler object.

        :param namespace_handler: An instance of a :class:`Namespace` subclass
                                  that handles all the event traffic for a
                                  namespace.
        """
        if not isinstance(namespace_handler, Namespace):
            raise_value_error("Not a namespace instance")
        if self.server is None:
            raise_runtime_error("SocketIO server is not initialized")

        self.server.register_namespace(namespace_handler)
        self.config["namespace_handlers"].append(namespace_handler)

    def unregister_namespace(self, namespace_handler: Namespace) -> None:
        """Unregister a namespace handler object.

        :param namespace_handler: An instance of a :class:`Namespace` subclass
                                  that handles all the event traffic for a
                                  namespace.
        """
        if not isinstance(namespace_handler, Namespace):
            raise_value_error("Not a namespace instance")
        if self.server is None:
            raise_runtime_error("SocketIO server is not initialized")
        namespace_handler._set_server(None)  # noqa: SLF001
        self.server.unregister_namespace(namespace_handler)
        self.config["namespace_handlers"].remove(namespace_handler)
