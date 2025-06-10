from __future__ import annotations

import asyncio
import logging
import sys
from os import getpid
from typing import TYPE_CHECKING, Any, AnyStr, Callable, Dict, List, Optional, Union

import socketio
from quart import Quart
from quart import json as quart_json
from werkzeug.debug import DebuggedApplication

from quart_socketio import Namespace
from quart_socketio._types import TCorsAllowOrigin, TQueueClassMap

if TYPE_CHECKING:
    import uvicorn

    if "hypercorn" in sys.modules:
        import hypercorn


class Controller:
    asgi_server_event: "uvicorn.Server" | "hypercorn.Server" | None = None
    shutdown_event = asyncio.Event()

    def __init__(self, app: Optional[Quart] = None, **kwargs: Union[str, bool, float, dict, None]) -> None:
        """
        Initialize the SocketIO server for async WebSocket communication.

        Args:
            app (Quart, optional): Quart application instance. If not provided,
                call `socketio.init_app(app)` later.
            **kwargs: Additional Socket.IO and Engine.IO server options.

        """
        self.server: Optional[socketio.AsyncServer] = None
        self.server_options: dict[str, Any] = {}

        # ASGI Application Server
        self.asgi_server_event = None

        # Handlers
        self.handlers: list[Callable[..., Any | None]] = []

        self.namespace_handlers: list[Namespace] = kwargs.get("namespace_handlers", [])

        # Callable Exception Handlers
        self.exception_handlers: dict[str, Callable[..., Any]] = kwargs.get("exception_handlers", {})
        self.default_exception_handler: Optional[Callable[..., Any]] = kwargs.get("default_exception_handler", None)

        # Boolean checks if the session is managed by this extension
        self.manage_session: bool = kwargs.get("manage_session", True)

        # Async mode and launch mode
        self.async_mode: str = kwargs.pop("async_mode", "asgi")
        self.launch_mode: str = kwargs.pop("launch_mode", "uvicorn")  # default to uvicorn, can be changed by the user

        # CORS allowed origins, default to '*'
        self.cors_allowed_origins: TCorsAllowOrigin = kwargs.pop("cors_allowed_origins", "*")

        # We can call init_app when:
        # - we were given the Quart app instance (standard initialization)
        # - we were not given the app, but we were given a message_queue
        #   (standard initialization for auxiliary process)
        # In all other cases we collect the arguments and assume the client
        # will call init_app from an app factory function.
        if app is not None or "message_queue" in kwargs:
            self.init_app(app, **kwargs)
        else:
            self.server_options.update(kwargs)

    async def client_manager(self, app: Quart) -> None:
        url: str = self.server_options.get("message_queue", None)
        channel: str = self.server_options.pop("channel", "quart-socketio")
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
            self.server_options["client_manager"] = queue

    async def json_setting(self, app: Quart):
        if "json" in self.server_options and self.server_options["json"] == quart_json:
            # Quart's json module is tricky to use because its output
            # changes when it is invoked inside or outside the app context
            # so here to prevent any ambiguities we replace it with wrappers
            # that ensure that the app context is always present
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

    async def run(
        self,
        app: Quart,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Run the SocketIO web server.

        :param app: The Quart application instance.
        :param host: The hostname or IP address for the server to listen on.
                     Defaults to 127.0.0.1.
        :param port: The port number for the server to listen on. Defaults to
                     5000.
        :param debug: ``True`` to start the server in debug mode, ``False`` to
                      start in normal mode.
        :param use_reloader: ``True`` to enable the Quart reloader, ``False``
                             to disable it.
        :param reloader_options: A dictionary with options that are passed to
                                 the Quart reloader, such as ``extra_files``,
                                 ``reloader_type``, etc.
        :param extra_files: A list of additional files that the Quart
                            reloader should watch. Defaults to ``None``.
                            Deprecated, use ``reloader_options`` instead.
        :param log_output: If ``True``, the server logs all incoming
                           connections. If ``False`` logging is disabled.
                           Defaults to ``True`` in debug mode, ``False``
                           in normal mode. Unused when the threading async
                           mode is used.
        :param kwargs: Additional web server options. The web server options
                       are specific to the server used in each of the supported
                       async modes. Note that options provided here will
                       not be seen when using an external web server such
                       as gunicorn, since this method is not called in that
                       case.
        :param async_mode: The async mode to use for the server. This can be
                          one of "uvicorn", or "hypercorn" (Default: uvicorn).
        """
        if host is None:
            host = "127.0.0.1"
        if port is None:
            server_name = app.config["SERVER_NAME"]
            if server_name and ":" in server_name:
                port = int(server_name.rsplit(":", 1)[1])
            else:
                port = 5000

        loggers: dict[str, Any] = {}
        logger_name = None
        config = kwargs.get("log_config")
        if config:
            logging.config.dictConfig(config)
            loggers: dict[str, Any] = config.get("loggers")
            logger_name = list(loggers.keys())[0] if loggers else None

        logger = logging.getLogger(logger_name)  # noqa: F841

        debug: bool = kwargs.pop("debug", app.debug)

        ssl: bool = kwargs.pop("ssl", False)  # noqa: F841
        addr_format = "%s://%s:%d" if ":" not in host else "%s://[%s]:%d"  # noqa: F841
        log_output: bool = kwargs.pop("log_output", debug)  # noqa: F841
        process_id = getpid()  # noqa: F841

        allow_unsafe_werkzeug = kwargs.pop("allow_unsafe_werkzeug", False)
        use_reloader: bool = kwargs.pop("use_reloader", debug)  # noqa: F841
        extra_files: Optional[List[str]] = kwargs.pop("extra_files", None)
        reloader_options: Dict[str, Any] = kwargs.pop("reloader_options", {})

        kw = {
            "app": app,
            "host": host,
            "port": port,
            "debug": debug,
            "use_reloader": use_reloader,
        }
        kw.update(kwargs)  # add any additional kwargs for hypercorn

        if extra_files:
            reloader_options["extra_files"] = extra_files

        async_mode = kwargs.get("launch_mode", self.launch_mode)

        # == Disabled unnecessary logging == #
        # message = "Started server process [%d]"
        # color_message = "Started server process [" + click.style("%d", fg="cyan") + "]"
        # logger.info(message, process_id, extra={"color_message": color_message})

        # == Disabled unnecessary logging == #
        # protocol_name = "https" if ssl else "http"
        # message = f"Quart-SocketIO running on {addr_format} \n (Press CTRL+C to quit)"
        # color_message = "".join((
        #     f"Quart-SocketIO running on {click.style(addr_format, bold=True)}",
        #     f"\n{click.style('(Press CTRL+C to quit)', fg='yellow')}",
        # ))
        # logger.info(
        #     message,
        #     protocol_name,
        #     host,
        #     port,
        #     extra={"color_message": color_message},
        # )

        app.debug = debug
        if app.debug and self.server.eio.async_mode != "threading":
            # put the debug middleware between the SocketIO middleware
            # and the Quart application instance
            #
            #    mw1   mw2   mw3   Quart app
            #     o ---- o ---- o ---- o
            #    /
            #   o Quart-SocketIO
            #    \  middleware
            #     o
            #  Quart-SocketIO WebSocket handler
            #
            # BECOMES
            #
            #  dbg-mw   mw1   mw2   mw3   Quart app
            #     o ---- o ---- o ---- o ---- o
            #    /
            #   o Quart-SocketIO
            #    \  middleware
            #     o
            #  Quart-SocketIO WebSocket handler
            #
            self.sockio_mw.wsgi_app = DebuggedApplication(self.sockio_mw.wsgi_app, evalex=True)

        if async_mode not in ["uvicorn", "hypercorn", "threading"]:
            raise ValueError(
                f"Invalid async_mode '{async_mode}'. Supported modes are 'uvicorn', 'hypercorn' and 'threading'."
            )

        if async_mode == "uvicorn":
            from quart_socketio._uvicorn import run_uvicorn

            await run_uvicorn(**kw)

        elif async_mode == "hypercorn":
            from quart_socketio._hypercorn import run_hypercorn

            await run_hypercorn(**kw)

        elif self.server.eio.async_mode == "threading":
            try:
                import simple_websocket  # noqa: F401
            except ImportError:
                from werkzeug._internal import _log

                _log(
                    "warning",
                    "WebSocket transport not available. Install simple-websocket for improved performance.",
                )
            if not sys.stdin or not sys.stdin.isatty():  # pragma: no cover
                if not allow_unsafe_werkzeug:
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
            app.run(
                host=host,
                port=port,
                threaded=True,
                use_reloader=use_reloader,
                **reloader_options,
                **kwargs,
            )

        # == Disabled unnecessary logging == #
        # message = "Finished server process [%d]"
        # color_message = "Finished server process [" + click.style("%d", fg="cyan") + "]"
        # logger.info(message, process_id, extra={"color_message": color_message})
        # == Disabled unnecessary logging == #

    # async def stop(self) -> None:
    #     """Stop a running SocketIO web server.

    #     This method must be called from a HTTP or SocketIO handler function.

    #     """
    #     if self.server.eio.async_mode == "hypercorn":
    #         raise SystemExit
    #     elif self.server.eio.async_mode == "uvicorn":
    #         await self.asgi_server_event.shutdown()
