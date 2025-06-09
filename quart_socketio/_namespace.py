from typing import Any, AnyStr

from socketio import Namespace as BaseNamespace

from quart_socketio import SocketIO


class Namespace(BaseNamespace):
    def __init__(self, namespace: str = None) -> None:
        super().__init__(namespace)
        self.socketio = None

    def _set_socketio(self, socketio: SocketIO) -> None:
        self.socketio = socketio

    async def trigger_event(self, event: str, *args: AnyStr | int | bool) -> Any:
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
        try:
            return self.socketio._handle_event(handler, event, self.namespace, *args)  # noqa: SLF001
        except TypeError as err:
            if event != "disconnect":
                raise TypeError(
                    f"Handler for event '{event}' in namespace '{self.namespace}' "
                    f"must accept at least one argument, the sid of the client"
                ) from err

            return self.socketio._handle_event(handler, event, self.namespace, *args[:-1])  # noqa: SLF001

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
