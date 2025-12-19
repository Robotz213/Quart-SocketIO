from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from engineio import AsyncServer as AsyncEIOServer
from socketio import AsyncServer

from ._types import P


class SocketIo(AsyncServer, AsyncEIOServer):
    eio: AsyncEIOServer


T = TypeVar("T")

type Function = Callable[P, T]
