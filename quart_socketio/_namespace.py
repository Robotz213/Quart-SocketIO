from __future__ import annotations

from typing import TYPE_CHECKING

from quart import Quart, request
from socketio import AsyncServer
from socketio import Namespace as BaseNamespace

from quart_socketio.common.exceptions import QuartSocketioError

if TYPE_CHECKING:
    from collections.abc import Callable

    from flask.sessions import SessionMixin

    from quart_socketio.typing import Function
    from quart_socketio.typing._types import P

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

        def get_handler[T]() -> Callable[P, T]:
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
        **kwargs: Any,
    ) -> Any:
        app: Quart = self.socketio.config.app
        config = self.socketio.config
        handler = kwargs.pop("handler", None)

        async with app.request_context(await self.make_request(**kwargs)):
            if not config.manage_session:
                await self.handle_session(request.namespace)

            return await handler()

    def _set_server(self, socketio: SocketIO) -> None:
        from . import SocketIO

        if not self.socketio:
            self.socketio = socketio

        if isinstance(socketio, SocketIO):
            self.server = socketio.server

        elif isinstance(socketio, AsyncServer):
            self.server = socketio

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
