from __future__ import annotations

from typing import Protocol

from engineio import AsyncServer as AsyncEIOServer
from socketio import AsyncServer

from ._types import P


class SocketIo(AsyncServer, AsyncEIOServer):
    eio: AsyncEIOServer


class Function[T](Protocol[P, T]): ...
