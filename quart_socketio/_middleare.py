from __future__ import annotations

from typing import Any, Callable

import socketio
from quart import Quart


class _SocketIOMiddleware(socketio.ASGIApp):
    """WSGI middleware simply exposes the Flask application in the WSGI environment before executing the request."""

    def __init__(self, socketio_app: socketio.ASGIApp, quart_app: Quart, socketio_path: str = "socket.io") -> None:
        self.quart_app = quart_app
        super().__init__(socketio_app, quart_app.asgi_app, socketio_path=socketio_path)

    async def __call__(self, environ: dict, start_response: Callable) -> Any:
        environ = environ.copy()
        environ["quart.app"] = self.quart_app
        return await super().__call__(environ, start_response)


__all__ = ["_SocketIOMiddleware"]
