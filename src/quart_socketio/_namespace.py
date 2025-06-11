from __future__ import annotations

from typing import TYPE_CHECKING, Any, AnyStr

from flask.sessions import SessionMixin
from socketio import AsyncServer
from socketio import Namespace as BaseNamespace

if TYPE_CHECKING:
    from . import SocketIO


class Namespace(BaseNamespace):
    def __init__(self, namespace: str = None, socketio: SocketIO = None) -> None:
        super().__init__(namespace)
        self.socketio = socketio

    def is_asyncio_based(self) -> bool:
        """Check if the namespace is asyncio-based."""
        return True

    def _set_server(self, socketio: SocketIO) -> None:
        from . import SocketIO

        if not self.socketio:
            self.socketio = socketio

        if isinstance(socketio, SocketIO):
            self.server = socketio.server

        elif isinstance(socketio, AsyncServer):
            self.server = socketio

    async def trigger_event(
        self, event: str, sid: str, environ: dict, *args: AnyStr | int | bool, **kwargs: AnyStr | int | bool
    ) -> Any:
        """Dispatch an event to the proper handler method.

        In the most common usage, this method is not overloaded by subclasses,
        as it performs the routing of events to methods. However, this
        method can be overridden if special dispatching rules are needed, or if
        having a single method that catches all events is desired.
        """
        handler_name = "on_" + (event or "")
        if not hasattr(self, handler_name):
            # there is no handler for this event, so we ignore it
            return
        handler = getattr(self, handler_name)
        kwrg = kwargs.copy()
        kwrg.update({
            "handler": handler,
            "event": event,
            "namespace": self.namespace,
            "sid": sid,
            "environ": environ,
        })

        if len(args) > 0:
            for item in args:
                if isinstance(item, dict):
                    kwrg.update({"data": item})
                elif getattr(self.socketio.reason, item, None) is not None:
                    kwrg.update({"reason": item})

        try:
            return await self.socketio._handle_event(**kwrg)  # noqa: SLF001
        except TypeError as err:
            if event != "disconnect":
                raise TypeError(
                    f"Handler for event '{event}' in namespace '{self.namespace}' "
                    f"must accept at least one argument, the sid of the client"
                ) from err

            return await self.socketio._handle_event(**kwrg)  # noqa: SLF001

    def emit(
        self,
        event: str,
        data: dict = None,
        room: str = None,
        include_self: bool = True,
        namespace: str = None,
        callback: callable = None,
    ) -> None:
        """Emit a custom event to one or more connected clients."""
        return self.socketio.emit(
            event, data, room=room, include_self=include_self, namespace=namespace or self.namespace, callback=callback
        )

    def send(
        self, data: dict, room: str = None, include_self: bool = True, namespace: str = None, callback: callable = None
    ) -> None:
        """Send a message to one or more connected clients."""
        return self.socketio.send(
            data, room=room, include_self=include_self, namespace=namespace or self.namespace, callback=callback
        )

    def close_room(self, room: str, namespace: str = None) -> None:
        """Close a room."""
        return self.socketio.close_room(room=room, namespace=namespace or self.namespace)

    async def save_session(self, sid: str, session: SessionMixin) -> None:
        return await self.server.save_session(sid, session, namespace=self.namespace)
