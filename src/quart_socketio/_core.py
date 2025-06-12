from __future__ import annotations

import asyncio
import base64
import json
import sys
from typing import TYPE_CHECKING, Any, AnyStr, Callable, Optional, Tuple, Union

import quart
import socketio
from flask import Request as FlaskRequest  # noqa: F401
from quart import Quart, Request, Websocket, session
from quart import Request as QuartRequest  # noqa: F401
from quart import json as quart_json
from quart.wrappers import Body
from werkzeug.datastructures.headers import Headers
from werkzeug.debug import DebuggedApplication

from quart_socketio._middleare import QuartSocketIOMiddleware
from quart_socketio._namespace import Namespace
from quart_socketio._types import TQueueClassMap
from quart_socketio.config.python_socketio import AsyncSocketIOConfig
from quart_socketio.config.quart_socketio import Config
from quart_socketio.test_client import SocketIOTestClient

from ._manager import _ManagedSession

if TYPE_CHECKING:
    import uvicorn

    if "hypercorn" in sys.modules:
        import hypercorn


class Controller:
    server: socketio.AsyncServer | None = None
    asgi_server: "uvicorn.Server" | "hypercorn.Server" | None = None
    shutdown_event = asyncio.Event()
    config: Config = None
    sockio_mw: socketio.ASGIApp | None = None
    server_options: AsyncSocketIOConfig = None

    def __init__(
        self,
        app: Optional[Quart] = None,
        config: Config = None,
        socket_config: AsyncSocketIOConfig = None,
        **kwargs: Union[str, bool, float, dict, None],
    ) -> None:
        """
        Initialize the SocketIO server for async WebSocket communication.

        Args:
            app (Quart, optional): Quart application instance. If not provided,
                call `socketio.init_app(app)` later.

            config (Config, optional): Configuration object for the SocketIO server.
            socket_config (AsyncSocketIOConfig, optional): Configuration for the
                Socket.IO server, including options like message queue, channel,
                and JSON handling.

            **kwargs: Additional Socket.IO and Engine.IO server options.

        """
        if config and not isinstance(config, Config):
            raise TypeError("config must be an instance of Config")

        if socket_config and not isinstance(socket_config, AsyncSocketIOConfig):
            raise TypeError("socket_config must be an instance of AsyncSocketIOConfig")

        self.config = config or kwargs.pop("config", Config(app=app, **kwargs))
        self.socket_config = socket_config or kwargs.pop("socket_config", AsyncSocketIOConfig(**kwargs))

        if app is not None or "message_queue" in kwargs:
            self.init_app(app=app, **kwargs)

    async def init_app(
        self,
        app: Quart,
        config: Config = None,
        socket_config: AsyncSocketIOConfig = None,
        **kwargs: Union[str, bool, float, dict, None],
    ) -> None:
        """
        Initialize the SocketIO extension for the given Quart application.

        :param app: The Quart application instance to initialize with SocketIO.
        :param kwargs: Additional keyword arguments for server configuration.
        """
        if not self.config:
            if config and not isinstance(config, Config):
                raise TypeError("config must be an instance of Config")
            self.config = config or kwargs.pop("config", Config(app=app, **kwargs))

        if not self.server_options:
            if socket_config and not isinstance(socket_config, AsyncSocketIOConfig):
                raise TypeError("socket_config must be an instance of AsyncSocketIOConfig")
            self.server_options = socket_config or kwargs.pop("server_options", AsyncSocketIOConfig(**kwargs))

        self.config.app = app
        self.config.update(**kwargs)
        self.server_options.update(**kwargs)

        self.server = socketio.AsyncServer(**self.server_options.to_dict())
        for handler in self.config.handlers:
            self.server.on(handler[0], handler[1], namespace=handler[2])

        for namespace_handler in self.config.namespace_handlers:
            self.server.register_namespace(namespace_handler)

        self.server._trigger_event = self._trigger_event

        if app is not None:
            # here we attach the SocketIO middleware to the SocketIO object so
            # it can be referenced later if debug middleware needs to be
            # inserted
            if not hasattr(app, "extensions"):
                app.extensions = {}  # pragma: no cover

            if "client_manager" not in kwargs:
                await self.client_manager(app)

            if self.server_options.json and self.server_options.json == quart_json:
                await self.json_setting(app)

            self.sockio_mw = QuartSocketIOMiddleware(self.server, app, socketio_path=self.server_options.socketio_path)
            app.asgi_app = self.sockio_mw
            app.extensions["socketio"] = self

    async def run(self, app: Quart = None, **kwargs: Union[str, bool, float, dict, None]) -> None:
        self.config.update(**kwargs)
        self.server_options = self.server_options.update(**kwargs)

        app = self.config.app

        if not app:
            raise ValueError("Quart application instance is required to run the server.")

        if self.config.extra_files:
            self.config.reloader_options["extra_files"] = self.config.extra_files

        async_mode = self.config.launch_mode
        app.debug = self.config.debug

        await self.update_socketio_middleware(app)

        if async_mode not in ["uvicorn", "hypercorn", "threading"]:
            raise ValueError(
                f"Invalid launch mode '{async_mode}'. Supported modes are 'uvicorn', 'hypercorn' and 'threading'."
            )

        if async_mode == "uvicorn":
            from quart_socketio._uvicorn import run_uvicorn

            await run_uvicorn(**self.config.to_dict())

        elif async_mode == "hypercorn":
            from quart_socketio._hypercorn import run_hypercorn

            await run_hypercorn(**self.config.to_dict())

        elif self.server.eio.async_mode == "threading":
            await self.threading_mode()

    async def client_manager(self, app: Quart) -> None:
        url = self.server_options.message_queue
        channel: str = self.server_options.channel
        write_only: bool = app is None
        if url:
            queue_class = socketio.KombuManager
            queue_class_map: TQueueClassMap = {
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

    async def json_setting(self, app: Quart) -> None:
        """
        Json settings for the Quart-SocketIO server.

        Quart's json module is tricky to use because its output
        changes when it is invoked inside or outside the app context
        so here to prevent any ambiguities we replace it with wrappers
        that ensure that the app context is always present

        Arguments:
            app (Quart): The Quart application instance to use for the context.

        """

        class QuartSafeJson:
            @staticmethod
            async def dumps(*args: str | int | bool, **kwargs: str | int | bool) -> str:
                with app.app_context():
                    return quart_json.dumps(*args, **kwargs)

            @staticmethod
            async def loads(*args: str | int | bool, **kwargs: str | int | bool) -> dict[str, AnyStr | int | bool]:
                async with app.app_context():
                    return quart_json.loads(*args, **kwargs)

        self.server_options["json"] = QuartSafeJson

    async def update_socketio_middleware(self, app: Quart) -> None:
        """
        Update the SocketIO middleware with the given app and configuration.

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
            self.sockio_mw.wsgi_app = DebuggedApplication(self.sockio_mw.wsgi_app, evalex=True)

    async def threading_mode(self) -> None:
        try:
            import simple_websocket  # noqa: F401
        except ImportError:
            from werkzeug._internal import _log

            _log(
                "warning",
                "WebSocket transport not available. Install simple-websocket for improved performance.",
            )
        if not sys.stdin or not sys.stdin.isatty():  # pragma: no cover
            if not self.config.allow_unsafe_werkzeug:
                raise RuntimeError(
                    "The Werkzeug web server is not "
                    "designed to run in production. Pass "
                    "allow_unsafe_werkzeug=True to the "
                    "run() method to disable this error."
                )
            else:
                from werkzeug._internal import _log

                _log(
                    "warning",
                    (
                        "Werkzeug appears to be used in a "
                        "production deployment. Consider "
                        "switching to a production web server "
                        "instead."
                    ),
                )

        app = self.config.app
        app.run(
            **self.config.to_dict(),
        )

    @classmethod
    def load_headers(cls, environ: dict[str, AnyStr]) -> Headers:
        """Load headers from the ASGI scope."""
        headers = Headers()

        io_headers: list[Tuple[AnyStr, AnyStr]] = environ["asgi.scope"]["headers"]
        for item1, item2 in io_headers:
            if isinstance(item1, bytes):
                item1 = item1.decode("utf-8")

            if isinstance(item2, bytes):
                item2 = item2.decode("utf-8")

            headers.add(item1.title(), item2)

        for key, value in list(environ.items()):
            if isinstance(value, Callable) or (key == "wsgi.input" or key == "asgi.input"):
                continue

            header_name = key
            if key.startswith("HTTP_"):
                header_name = key.split("_")[-1].title()
                if isinstance(value, bytes):
                    value = value.decode("utf-8")

            elif isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, str):
                        try:
                            if isinstance(v, bytes):
                                v = v.decode("utf-8")

                        except UnicodeDecodeError:
                            # If decoding fails, keep it as bytes
                            pass
                        headers.add(k.title(), v)

            headers.add(header_name, value)

        return headers

    async def handle_session(self, environ: dict[str, str | dict[str, Any]]) -> None:
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
            else session._get_current_object()
        )  # noqa: SLF001
        ctx = (
            quart.globals.websocket_ctx._get_current_object()
            if hasattr(quart, "globals") and hasattr(quart.globals, "websocket_ctx")
            else quart._websocket_ctx_stack.top
        )  # noqa: SLF001
        if self.config.manage_session:
            ctx.session = session_obj

        # when Quart is managing the user session, it needs to save it
        if not hasattr(session_obj, "modified") or session_obj.modified:
            resp = app.response_class()
            app.session_interface.save_session(app, session_obj, resp)

    async def make_request(self, **kwargs: AnyStr) -> Request:
        kwargs = kwargs or {}
        data = kwargs.get("data", {})

        environ = self.server.get_environ(kwargs["sid"], namespace=kwargs.get("namespace", None))

        try:
            req = Request(  # noqa: F841
                method=environ["REQUEST_METHOD"],
                scheme=environ["asgi.scope"].get("scheme", "http"),
                path=environ["PATH_INFO"],
                query_string=environ["asgi.scope"]["query_string"],
                headers=await self.load_headers(environ),
                root_path=environ["asgi.scope"].get("root_path", ""),
                http_version=environ["SERVER_PROTOCOL"],
                scope=environ["asgi.scope"],
                send_push_promise=self.send_push_promise,
            )

            req.sid = kwargs.get("sid", None)

            new_data = {}
            for k, v in list(data.items()):
                if isinstance(v, bytes):
                    v = base64.b64encode(v).decode("utf-8")
                if isinstance(v, dict):
                    for key, value in v.items():
                        if isinstance(value, bytes):
                            v[key] = base64.b64encode(value).decode("utf-8")

                if isinstance(v, (list, tuple)):
                    v = [base64.b64encode(item).decode("utf-8") if isinstance(item, bytes) else item for item in v]

                new_data[k] = v

            data = new_data
            parsejson = json.dumps(data).encode("utf-8")
            body = Body(len(parsejson), len(parsejson))
            body.append(parsejson)
            req.body = body

        except Exception as e:  # noqa: F841
            raise

        return req

    async def make_websocket(self, **kwargs: AnyStr) -> Request:
        kwargs = kwargs or {}
        try:
            environ = self.server.get_environ(kwargs["sid"], namespace=kwargs["namespace"])
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
        except Exception:
            raise

        return websock

    async def register_handler(self, handler_args: Tuple[str, Callable[..., Any], str]) -> None:
        """Register a SocketIO event handler.

        This method is used to register an event handler without using the
        decorator syntax. It is useful for dynamically registering handlers.

        :param handler_args: A tuple containing the event name, handler function,
                             and namespace.
        """
        event, handler, namespace = handler_args
        self.on(event=event, namespace=namespace)(handler)

    def test_client(
        self,
        app: Quart,
        namespace: Optional[str] = None,
        query_string: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        auth: Optional[dict[str, Any]] = None,
        quart_test_client: Any = None,
    ) -> SocketIOTestClient:
        """The Socket.IO test client is useful for testing a Quart-SocketIO server.

        It works in a similar way to the Quart Test Client, but
        adapted to the Socket.IO server.

        :param app: The Quart application instance.
        :param namespace: The namespace for the client. If not provided, the
                          client connects to the server on the global
                          namespace.
        :param query_string: A string with custom query string arguments.
        :param headers: A dictionary with custom HTTP headers.
        :param auth: Optional authentication data, given as a dictionary.
        :param quart_test_client: The instance of the Quart test client
                                  currently in use. Passing the Quart test
                                  client is optional, but is necessary if you
                                  want the Quart user session and any other
                                  cookies set in HTTP routes accessible from
                                  Socket.IO events.
        """
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
            raise ValueError("Not a namespace instance")
        if self.server is None:
            raise RuntimeError("SocketIO server is not initialized")

        namespace_handler._set_server(self)
        self.server.register_namespace(namespace_handler)
        self.config.namespace_handlers.append(namespace_handler)

    async def unregister_namespace(self, namespace_handler: Namespace) -> None:
        """Unregister a namespace handler object.

        :param namespace_handler: An instance of a :class:`Namespace` subclass
                                  that handles all the event traffic for a
                                  namespace.
        """
        if not isinstance(namespace_handler, Namespace):
            raise ValueError("Not a namespace instance")
        if self.server is None:
            raise RuntimeError("SocketIO server is not initialized")
        namespace_handler._set_server(None)
        self.server.unregister_namespace(namespace_handler)
        self.config.namespace_handlers.remove(namespace_handler)

    # async def stop(self) -> None:
    #     """Stop a running SocketIO web server.

    #     This method must be called from a HTTP or SocketIO handler function.

    #     """
    #     if self.server.eio.async_mode == "hypercorn":
    #         raise SystemExit
    #     elif self.server.eio.async_mode == "uvicorn":
    #         await self.asgi_server.shutdown()
