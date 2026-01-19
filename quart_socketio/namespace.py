from __future__ import annotations

import traceback
from asyncio import iscoroutinefunction
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
        sid: str,
        event: str,
        namespace: str,
        environ: dict[str, Any],
        data: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        """Dispatch an event to the proper handler method.

        In the most common usage, this method is not overloaded by subclasses,
        as it performs the routing of events to methods. However, this
        method can be overridden if special dispatching rules are needed, or if
        having a single method that catches all events is desired.
        """
        handler = self.get_handler(event=event)
        if handler:
            try:
                return await self._handle_event(
                    handler=handler,
                    sid=sid,
                    event=event,
                    namespace=namespace,
                    environ=environ,
                    data=data,
                )

            except TypeError as err:
                if event != "disconnect":
                    raise QuartSocketioError(err) from err

                return await self._handle_event(
                    handler=handler,
                    sid=sid,
                    event=event,
                    namespace=namespace,
                    environ=environ,
                    data=data,
                )

            except Exception as e:
                err_more = "".join(traceback.format_exception(e))  # noqa: F841
                err = "".join(traceback.format_exception_only(e))
                self.socketio.app.logger.exception(err)
                return err

        return self.server.not_handled

    async def _handle_event[**P, T](
        self,
        data: dict[str, Any],
        event: str,
        namespace: str | None,
        sid: str | None,
        environ: dict[str, Any] | None = None,
        handler: Callable[P, T] | None = None,
    ) -> Any:
        app: Quart = self.sockio_mw.quart_app
        if event == "disconnect":
            try:
                if iscoroutinefunction(handler):
                    return await handler(**data)

                return handler(**data)

            except SocketIOConnectionRefusedError:
                raise  # let this error bubble up to python-socketio
            except Exception as e:
                err_more = "".join(traceback.format_exception(e))
                err = "".join(traceback.format_exception_only(e))
                app.logger.exception(err)
                return err

        request_ctx_sio = await self.make_request(
            environ=environ,
            sid=sid,
            namespace=namespace,
        )
        async with app.request_context(request_ctx_sio):
            if not self.socketio.config["manage_session"]:
                await self.handle_session(request.namespace)

            try:
                if iscoroutinefunction(handler):
                    return await handler(**data)

                return handler(**data)

            except SocketIOConnectionRefusedError:
                raise  # let this error bubble up to python-socketio
            except Exception as e:
                err_more = "".join(traceback.format_exception(e))  # noqa: F841
                err = "".join(traceback.format_exception_only(e))
                app.logger.exception(err)
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
        self.sockio_mw = socketio.sockio_mw

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
            event=event,
            data=data,
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
            data=data,
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
            sid=sid,
            session=session,
            namespace=self.namespace,
        )

    def get_handler[**P, T](self, event: str) -> Callable[P, T]:
        return getattr(self, "on_" + (event or ""), None)
