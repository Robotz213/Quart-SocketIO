from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from quart import Quart, request
from socketio import AsyncNamespace as BaseNamespace
from socketio import AsyncServer

from quart_socketio.common.exceptions import QuartSocketioError
from quart_socketio.main import SocketIOConnectionRefusedError

if TYPE_CHECKING:
    from collections.abc import Callable

    from flask.sessions import SessionMixin

    from quart_socketio.typing import Function

    from . import SocketIO

type Any = any


class Namespace(BaseNamespace):
    def __init__(
        self,
        namespace: str | None = None,
        socketio: SocketIO = None,
    ) -> None:
        super().__init__(namespace)
        self.socketio = socketio

    def is_asyncio_based(self) -> bool:
        """Check if the namespace is asyncio-based."""
        return True

    async def make_request(self, **kwargs: Any) -> dict[str, Any]:
        """Create a request dictionary for the namespace."""
        return await self.socketio.make_request(**kwargs)

    async def make_websocket(self, **kwargs: Any) -> dict[str, Any]:
        """Create a websocket dictionary for the namespace."""
        return await self.socketio.make_websocket(**kwargs)

    async def trigger_event(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Dispatch an event to the proper handler method.

        In the most common usage, this method is not overloaded by subclasses,
        as it performs the routing of events to methods. However, this
        method can be overridden if special dispatching rules are needed, or if
        having a single method that catches all events is desired.
        """
        sid: str = args[2]
        event: str = args[0] if len(args) > 1 and args[0] != "*" else sid
        _namespace: str = args[1] if len(args) > 2 and args[1] != "*" else sid

        def get_handler[**P, T]() -> Callable[P, T]:
            return getattr(self, "on_" + (event or ""), None)

        handler = get_handler()
        if handler:
            try:
                return await self._handle_event(*args, **kwargs)
            except TypeError as err:
                if event != "disconnect":
                    raise QuartSocketioError(err) from err

                return await self._handle_event(*args, **kwargs)

        return self.server.not_handled

    async def _handle_event(
        self,
        event: str,
        namespace: str | None,
        sid: str | None,
        environ: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        app: Quart = self.sockio_mw.quart_app

        handler = kwargs.pop("handler", None)

        request_ctx_sio = await self.make_request(environ=environ)
        async with app.request_context(request_ctx_sio):
            if not self.config["manage_session"]:
                await self.handle_session(request.namespace)

            try:
                return await handler(*args, **kwargs)

            except SocketIOConnectionRefusedError:
                raise  # let this error bubble up to python-socketio
            except Exception as e:  # noqa: BLE001
                err_more = "".join(traceback.format_exception(e))  # noqa: F841
                err = "".join(traceback.format_exception_only(e))
                self.config["app"].error(err)
                return err

    def _set_server(self, socketio: SocketIO) -> None:
        from . import SocketIO

        if not self.socketio:
            self.socketio = socketio

        if isinstance(socketio, SocketIO):
            self.server = socketio.server

        elif isinstance(socketio, AsyncServer):
            self.server = socketio

    def set_socketio(self, socketio: SocketIO) -> None:

        self._set_server(socketio)

    def _set_socketio(self, socketio: SocketIO) -> None:

        self._set_server(socketio)

    def emit(
        self,
        event: str,
        data: dict | None = None,
        room: str | None = None,
        *,
        include_self: bool = True,
        namespace: str | None = None,
        callback: Function = None,
    ) -> None:
        """Emit a custom event to one or more connected clients."""
        return self.socketio.emit(
            event,
            data,
            room=room,
            include_self=include_self,
            namespace=namespace or self.namespace,
            callback=callback,
        )

    def send(
        self,
        data: dict,
        room: str | None = None,
        *,
        include_self: bool = True,
        namespace: str | None = None,
        callback: Function = None,
    ) -> None:
        """Send a message to one or more connected clients."""
        return self.socketio.send(
            data,
            room=room,
            include_self=include_self,
            namespace=namespace or self.namespace,
            callback=callback,
        )

    def close_room(self, room: str, namespace: str | None = None) -> None:
        """Close a room."""
        return self.socketio.close_room(
            room=room,
            namespace=namespace or self.namespace,
        )

    async def save_session(self, sid: str, session: SessionMixin) -> None:
        return await self.server.save_session(
            sid,
            session,
            namespace=self.namespace,
        )
