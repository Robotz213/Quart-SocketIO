from __future__ import annotations

import base64  # noqa: F401
from asyncio import Event
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    AnyStr,
    Literal,
    overload,
)

import quart
import socketio
from quart import Quart, Request, Websocket, session
from quart import json as quart_json
from werkzeug.datastructures.headers import Headers
from werkzeug.debug import DebuggedApplication
from werkzeug.test import EnvironBuilder  # noqa: F401

from quart_socketio._middleare import QuartSocketIOMiddleware
from quart_socketio._namespace import Namespace
from quart_socketio._utils import FormParserQuartSocketio, parse_provided_data
from quart_socketio.common.exceptions import (
    raise_runtime_error,
    raise_value_error,
)
from quart_socketio.config import Config
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
        LaunchMode,
        QueueClasses,
        QueueClassMap,
        SocketIo,
        Transports,
    )
    from quart_socketio.typing._quart import CustomJsonClass


class Controller:
    server: SocketIo | None = None
    asgi_server: Server | HypercornServer | None = None
    shutdown_event = Event()
    config: Config = None
    sockio_mw: socketio.ASGIApp | None = None

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
        launch_mode: LaunchMode,
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

        if app is not None or "message_queue" in self.config:
            self.init_app(app=app, **kwargs)

    async def init_app(
        self,
        app: Quart,
        **kwargs: Kw,
    ) -> None:
        """Initialize the SocketIO extension for the given Quart application.

        :param app: The Quart application instance to initialize with SocketIO.
        :param kwargs: Additional keyword arguments for server configuration.
        """
        self.config.update(app=app)
        self.config.update(**kwargs)

        if app is not None:
            if not hasattr(app, "extensions"):
                app.extensions = {}  # pragma: no cover

            if "client_manager" not in kwargs:
                self.client_manager(app)

            if (
                self.server_options.json
                and self.server_options.json == quart_json
            ):
                self.json_setting(app)

            self.sockio_mw = QuartSocketIOMiddleware(
                self.server,
                app,
                socketio_path=self.server_options.socketio_path,
            )
            app.asgi_app = self.sockio_mw
            app.extensions["socketio"] = self

    async def run(
        self,
        app: Quart = None,
        **kwargs: type[Any],
    ) -> None:
        self.config.update(**kwargs)
        self.server_options = self.server_options.update(**kwargs)

        app = self.config.app

        if not app:
            raise_value_error(
                "Quart application instance is required to run the server.",
            )

        if self.config.extra_files:
            self.config.reloader_options["extra_files"] = (
                self.config.extra_files
            )

        async_mode = self.config.launch_mode
        app.debug = self.config.debug

        await self.update_socketio_middleware(app)

        if async_mode not in ["uvicorn", "hypercorn", "threading"]:
            raise_value_error(
                (
                    f"Invalid launch mode '{async_mode}'."
                    "Supported modes are 'uvicorn', 'hypercorn'."
                ),
            )

        if async_mode == "uvicorn":
            from quart_socketio._uvicorn import run_uvicorn

            await run_uvicorn(**self.config.to_dict())

        elif async_mode == "hypercorn":
            from quart_socketio._hypercorn import run_hypercorn

            await run_hypercorn(**self.config.to_dict())

        elif self.server.eio.async_mode == "threading":
            await self.threading_mode()

    def client_manager(self, app: Quart) -> None:
        url = self.server_options.message_queue
        channel: str = self.server_options.channel
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
            self.server_options.client_manager = queue

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
                with app.app_context():
                    return quart_json.dumps(*args, **kwargs)

            @staticmethod
            async def loads(
                *args: str | int | bool,
                **kwargs: str | int | bool,
            ) -> dict[str, AnyStr | int | bool]:
                async with app.app_context():
                    return quart_json.loads(*args, **kwargs)

        self.config["json"] = QuartSafeJson

    async def update_socketio_middleware(self, app: Quart) -> None:
        """Update the SocketIO middleware with the given app and configuration.

        Put the debug middleware between the SocketIO middleware
        and the Quart application instance
        """
        #    mw1    mw2    mw3   Quart app
        #     o ---- o ---- o ---- o
        #     /
        #    o Quart-SocketIO
        #     \  middleware
        #     o
        #    Quart-SocketIO WebSocket handler

        #    dbg-mw  mw1   mw2    mw3  Quart app
        #     o ---- o ---- o ---- o ---- o
        #     /
        #    o Quart-SocketIO
        #     \  middleware
        #     o
        #    Quart-SocketIO WebSocket handler

        if app.debug and self.config.launch_mode != "threading":
            self.sockio_mw.wsgi_app = DebuggedApplication(
                self.sockio_mw.wsgi_app,
                evalex=True,
            )

    @classmethod
    def load_headers(cls, environ: dict[str, AnyStr]) -> Headers:  # noqa: C901
        """Load headers from the ASGI scope."""
        headers = Headers()

        io_headers: list[tuple[AnyStr, AnyStr]] = environ["asgi.scope"][
            "headers"
        ]
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
        app = self.config.app

        session_obj: _ManagedSession | Any = (
            environ.setdefault("saved_session", _ManagedSession(session))
            if self.config.manage_session
            else session._get_current_object()  # noqa: SLF001
        )
        ctx = (
            quart.globals.websocket_ctx._get_current_object()  # noqa: SLF001
            if hasattr(quart, "globals")
            and hasattr(quart.globals, "websocket_ctx")
            else quart._websocket_ctx_stack.top  # noqa: SLF001
        )
        if self.config.manage_session:
            ctx.session = session_obj

        # when Quart is managing the user session, it needs to save it
        if not hasattr(session_obj, "modified") or session_obj.modified:
            resp = app.response_class()
            app.session_interface.save_session(app, session_obj, resp)

    async def make_request(self, **kwargs: AnyStr) -> Request:
        kwargs = kwargs or {}
        data = kwargs.get("data", kwargs.get("json", kwargs.get("form", {})))

        environ = self.server.get_environ(
            kwargs["sid"],
            namespace=kwargs.get("namespace", None),
        )
        data_req = await parse_provided_data(data)
        req = Request(
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
        req.form_data_parser_class = FormParserQuartSocketio

        req.sid = kwargs.get("sid", None)
        req.socket_data = data_req

        return req

    async def make_websocket(self, **kwargs: AnyStr) -> Request:
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
        namespace: str | None = None,
        query_string: str | None = None,
        headers: dict[str, str] | None = None,
        auth: dict[str, Any] | None = None,
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

    async def register_namespace(self, namespace_handler: Namespace) -> None:
        """Register a namespace handler object.

        :param namespace_handler: An instance of a :class:`Namespace` subclass
                                  that handles all the event traffic for a
                                  namespace.
        """
        if not isinstance(namespace_handler, Namespace):
            raise_value_error("Not a namespace instance")
        if self.server is None:
            raise_runtime_error("SocketIO server is not initialized")

        namespace_handler._set_server(self)  # noqa: SLF001
        self.server.register_namespace(namespace_handler)
        self.config.namespace_handlers.append(namespace_handler)

    async def unregister_namespace(self, namespace_handler: Namespace) -> None:
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
        self.config.namespace_handlers.remove(namespace_handler)
