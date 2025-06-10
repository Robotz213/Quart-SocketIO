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
from quart_socketio._types import TQueueClassMap
from quart_socketio.config import AsyncSocketIOConfig, Config

if TYPE_CHECKING:
    import uvicorn

    if "hypercorn" in sys.modules:
        import hypercorn


class Controller:
    asgi_server: "uvicorn.Server" | "hypercorn.Server" | None = None
    shutdown_event = asyncio.Event()
    config = Config
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
        if not config:
            self.config = Config(app=app, **kwargs)

        if not socket_config:
            self.server_options = AsyncSocketIOConfig(**kwargs)

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

             mw1    mw2    mw3   Quart app
              o ---- o ---- o ---- o
             /
            o Quart-SocketIO
             \  middleware
              o
            Quart-SocketIO WebSocket handler


            dbg-mw  mw1    mw2    mw3  Quart app
              o ---- o ---- o ---- o ---- o
             /
            o Quart-SocketIO
             \  middleware
              o
            Quart-SocketIO WebSocket handler

        """  # noqa: D301, D413, W605
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

    # async def stop(self) -> None:
    #     """Stop a running SocketIO web server.

    #     This method must be called from a HTTP or SocketIO handler function.

    #     """
    #     if self.server.eio.async_mode == "hypercorn":
    #         raise SystemExit
    #     elif self.server.eio.async_mode == "uvicorn":
    #         await self.asgi_server.shutdown()
