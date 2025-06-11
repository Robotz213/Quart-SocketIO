from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any, AnyStr, Callable

from flask.sessions import SessionMixin
from quart import Quart, request
from socketio import AsyncServer
from socketio import Namespace as BaseNamespace
from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError

if TYPE_CHECKING:
    from . import SocketIO


class Namespace(BaseNamespace):
    def __init__(self, namespace: str = None, socketio: SocketIO = None) -> None:
        super().__init__(namespace)
        self.socketio = socketio

    def is_asyncio_based(self) -> bool:
        """Check if the namespace is asyncio-based."""
        return True

    async def trigger_event(
        self,
        *args: AnyStr | int | bool | dict[str, AnyStr],
        **kwargs: AnyStr | int | bool | dict[str, AnyStr],
    ) -> Any:
        """Dispatch an event to the proper handler method.

        In the most common usage, this method is not overloaded by subclasses,
        as it performs the routing of events to methods. However, this
        method can be overridden if special dispatching rules are needed, or if
        having a single method that catches all events is desired.
        """
        config = self.socketio.config

        sid: str = args[2]
        event: str = args[0] if len(args) > 1 and args[0] != "*" else sid
        namespace: str = args[1] if len(args) > 2 and args[1] != "*" else sid

        def get_handler() -> Callable[..., Any] | None:
            return getattr(self, "on_" + (event or ""), None)

        handler = get_handler()

        if handler:
            environ = args[3]

            ignore_data = [sid, event, namespace, environ]

            data = {
                k: v
                for x in args
                if not any(x == item for item in ignore_data)
                for k, v in list(x.items())
                if isinstance(x, dict) and k not in ignore_data
            }

            if config.app.extensions.get("quart-jwt-extended"):
                for item in data:
                    header_name = config.app.config.get("JWT_HEADER_NAME", "Authorization")

                    if isinstance(item, dict):
                        for k, _ in list(item.items()):
                            if header_name in k:
                                environ[header_name] = item[k]
                                break

            kwrg = kwargs.copy()
            kwrg.update({
                "handler": handler,
                "event": event,
                "namespace": namespace,
                "sid": sid,
                "environ": environ,
                "data": data,
            })

            if len(args) > 0:
                for item in args:
                    if isinstance(item, str) and getattr(self.server.reason, item.replace(" ", "_").upper(), None):
                        kwrg.update({"reason": item})
                        break

            try:
                return await self._handle_event(**kwrg)
            except TypeError as err:
                if event != "disconnect":
                    raise TypeError(
                        f"Handler for event '{event}' in namespace '{namespace}' "
                        f"must accept at least one argument, the sid of the client"
                    ) from err

                return await self._handle_event(**kwrg)

        return self.server.not_handled

    async def _handle_event(
        self,
        **kwargs: Any,
    ) -> Any:
        app: Quart = self.socketio.config.app
        config = self.socketio.config
        handler = kwargs.pop("handler", None)

        async with app.request_context(await self.make_request(**kwargs)):
            async with app.websocket_context(await self.make_websocket(**kwargs)):
                if not config.manage_session:
                    await self.handle_session(request.namespace)

                try:
                    return await handler()

                except SocketIOConnectionRefusedError:
                    raise  # let this error bubble up to python-socketio
                except Exception as e:
                    err_more = "".join(traceback.format_exception(e))  # noqa: F841
                    err = "".join(traceback.format_exception_only(e))
                    config.app.logger.error(err)
                    return err

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
