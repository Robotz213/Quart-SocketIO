from __future__ import annotations  # noqa: D104

import io  # noqa: F401
import json  # noqa: F401
import traceback
from functools import wraps
from typing import Any, AnyStr, Callable, Coroutine, Optional

import click  # noqa: F401
import socketio
from quart import Quart, has_request_context
from quart import websocket as request
from quart.datastructures import FileStorage  # noqa: F401
from quart.wrappers import Body  # noqa: F401
from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError
from werkzeug.datastructures.headers import Headers

from quart_socketio._core import Controller
from quart_socketio._types import TExceptionHandler, TFunction

from ._namespace import Namespace
from ._utils import (
    call,
    close_room,
    disconnect,
    emit,
    join_room,
    leave_room,
    rooms,
    send,
)
from .test_client import SocketIOTestClient

__all__ = [
    "close_room",
    "disconnect",
    "emit",
    "call",
    "send",
    "join_room",
    "leave_room",
    "rooms",
    "Namespace",
    "SocketIOTestClient",
]


class SocketIO(Controller):
    """
    SocketIO extension for Quart, enabling async WebSocket communication using the Socket.IO protocol.

    This class provides integration between Quart and python-socketio, allowing you to handle real-time
    bi-directional communication between clients and your Quart application. It supports broadcasting,
    rooms, namespaces, background tasks, and multi-process setups via message queues.

    Arguments:
        app (Optional[Quart]): The Quart application instance.
        manage_session (bool, optional): If True, manages user sessions for Socket.IO events separately.
            Set to False to use Quart's session management, which is recommended for server-side sessions.
        message_queue (str, optional): URL for a message queue (e.g., Redis, Kafka, ZMQ, Kombu) to enable
            multi-process communication. Not required for single-process deployments.
        channel (str, optional): Channel name for the message queue. Use different channels for separate
        path (str, optional): URL path where the Socket.IO server is exposed. Defaults to 'socket.io'.
        cors_allowed_origins (str, list, or callable, optional): Allowed origins for CORS. Defaults to '*'.
        async_mode (str, optional): Async mode to use. Options: 'uvicorn', 'hypercorn'. Defaults to 'uvicorn'.
        launch_mode (str, optional): Alias for async_mode.
        **kwargs: Additional options for Socket.IO and Engine.IO servers.
        client_manager: Custom client manager instance. Defaults to in-memory manager.
        logger: Enable logging (True or logger object) or disable (False).
        json: Custom JSON module for encoding/decoding packets. Use `quart.json` for Quart compatibility.
        async_handlers: If True, event handlers run in separate threads. If False, run synchronously.
        always_connect: If True, connections are accepted immediately. If False, connections are provisional
            until the connect handler returns non-False.
        async_mode: Async model to use. Options: 'threading', 'eventlet', 'gevent', 'gevent_uwsgi'.
            If not set, tries in order: 'eventlet', 'gevent_uwsgi', 'gevent', 'threading'.
        ping_timeout: Seconds client waits for server response before disconnecting. Default: 5.
        max_http_buffer_size: Max message size for polling transport. Default: 1,000,000 bytes.
        http_compression: Enable compression for polling transport. Default: True.
        compression_threshold: Only compress messages above this size (bytes). Default: 1024.
        cookie: Name of HTTP cookie for session id, or dict with cookie attributes, or None to disable.
        cors_allowed_origins: Origin(s) allowed to connect. Default: same origin. Use '*' to allow all.
        cors_credentials: Allow credentials (cookies, auth) in requests. Default: True.
        monitor_clients: If True, background task closes inactive clients. Default: True.
        engineio_logger: Enable Engine.IO logs (True or logger), or disable (False). Default: False.

    Attributes:
        server (Optional[socketio.AsyncServer]): The underlying Socket.IO server instance.
        server_options (dict): Options passed to the Socket.IO server.
        asgi_server_event: Reference to the ASGI server instance.
        handlers (list): Registered event handlers.
        namespace_handlers (list): Registered namespace handler instances.
        exception_handlers (dict): Custom exception handlers per namespace.
        default_exception_handler (Optional[Callable]): Default exception handler.
        manage_session (bool): Whether to manage sessions for Socket.IO events.
        async_mode (str): The async mode in use.
        launch_mode (str): The launch mode/server backend.
        cors_allowed_origins (str, list, or callable): Allowed CORS origins.

    Example:
        ```python
        from quart import Quart
        from quart_socketio import SocketIO

        app = Quart(__name__)
        socketio = SocketIO(app, async_mode="asgi")


        @socketio.on("message")
        async def handle_message(data):
            print("Received:", data)
            await socketio.emit("response", {"ok": True})


        if __name__ == "__main__":
            asyncio.run(socketio.run(app))

            # Or
            async def main():
                await socketio.run(app)

            asyncio.run(main())
        ```

    """

    reason: socketio.AsyncServer.reason = socketio.AsyncServer.reason

    async def _trigger_event(
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
        sid: str = args[2]
        event: str = args[0] if len(args) > 1 and args[0] != "*" else sid
        namespace: str = args[1] if len(args) > 2 and args[1] != "*" else sid

        def get_handler() -> Callable[..., Any] | None:
            filter_ = list(filter(lambda x: x[0] == event and x[2] == namespace, self.config.handlers))
            return filter_[0][1] if len(filter_) > 0 else None

        handler = get_handler()
        namespace_handler, _ = self.server._get_namespace_handler(namespace, args)

        if handler:
            environ = args[3]

            ignore_data = [sid, event, namespace, environ]

            data = {}
            for x in args:
                if x and not any(x == item for item in ignore_data):
                    for k, v in list(x.items()):
                        if isinstance(x, dict) and k not in ignore_data:
                            data[k] = v

            if self.config.app.extensions.get("quart-jwt-extended"):
                for item in data:
                    header_name = self.config.app.config.get("JWT_HEADER_NAME", "Authorization")

                    if isinstance(item, dict):
                        for k, _ in list(item.items()):
                            if header_name in k:
                                environ[header_name] = item[k]
                                break

            kwrg = kwargs.copy()
            kwrg.update({
                "event": event,
                "namespace": namespace,
                "sid": sid,
                "environ": environ,
                "data": data,
            })

            if len(args) > 0:
                for item in args:
                    if isinstance(item, str) and getattr(self.reason, item.replace(" ", "_").upper(), None):
                        kwrg.update({"reason": item})
                        break

            try:
                return await handler(**kwrg)  # noqa: SLF001
            except TypeError as err:
                if event != "disconnect":
                    raise TypeError(
                        f"Handler for event '{event}' in namespace '{namespace}' "
                        f"must accept at least one argument, the sid of the client"
                    ) from err

                return await handler(**kwrg)  # noqa: SLF001

        elif namespace_handler:
            return await namespace_handler.trigger_event(*args, **kwargs)

        return self.server.not_handled

    async def _handle_event(
        self,
        **kwargs: Any,
    ) -> Any:
        app: Quart = self.sockio_mw.quart_app

        handler = kwargs.pop("handler", None)

        async with app.request_context(await self.make_request(**kwargs)):
            async with app.websocket_context(await self.make_websocket(**kwargs)):
                if not self.config.manage_session:
                    await self.handle_session(request.namespace)

                try:
                    return await handler()

                except SocketIOConnectionRefusedError:
                    raise  # let this error bubble up to python-socketio
                except Exception as e:
                    err_more = "".join(traceback.format_exception(e))  # noqa: F841
                    err = "".join(traceback.format_exception_only(e))
                    self.config.app.logger.error(err)
                    return err

    def on(self, event: str, namespace: str = "/") -> Callable[[TFunction], TFunction]:
        """Register a SocketIO event handler.

        This decorator must be applied to SocketIO event handlers. Example::

            @socketio.on("my event", namespace="/chat")
            async def handle_my_custom_event(json):
                print("received json: " + str(json))

        :param event: The name of the event. This is normally a user defined
                        string, but a few event names are already defined. Use
                        ``'message'`` to define a handler that takes a string
                        payload, ``'json'`` to define a handler that takes a
                        JSON blob payload, ``'connect'`` or ``'disconnect'``
                        to create handlers for connection and disconnection
                        events.
        :param namespace: The namespace on which the handler is to be
                          registered. Defaults to the global namespace.

        """

        def decorator(handler: TFunction) -> TFunction:
            @wraps(handler)
            async def _handler(
                **kwargs: str | int | bool,
            ) -> AnyStr | int | bool:
                """Process the event."""
                kwargs = kwargs.copy()
                kwargs.update({"handler": handler})
                try:
                    return await self._handle_event(**kwargs)  # noqa: SLF001
                except TypeError as err:
                    if event != "disconnect":
                        raise TypeError(
                            f"Handler for event '{event}' in namespace '{namespace}' "
                            f"must accept at least one argument, the sid of the client"
                        ) from err

                    return await self._handle_event(**kwargs)  # noqa: SLF001

            self.config.handlers.append((event, _handler, namespace))
            return handler

        return decorator

    def event(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an event handler.

        This is a simplified version of the ``on()`` method that takes the
        event name from the decorated function.

        Example usage::

            @socketio.event
            def my_event(data):
                print("Received data: ", data)

        The above example is equivalent to::

            @socketio.on("my_event")
            def my_event(data):
                print("Received data: ", data)

        A custom namespace can be given as an argument to the decorator::

            @socketio.event(namespace="/test")
            def my_event(data):
                print("Received data: ", data)

        """
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # the decorator was invoked without arguments
            # args[0] is the decorated function
            return self.on(args[0].__name__)(args[0])
        else:
            # the decorator was invoked with arguments
            def set_handler(handler):  # noqa: ANN001, ANN202
                return self.on(handler.__name__, *args, **kwargs)(handler)

            return set_handler

    def on_namespace(self, namespace_handler: Namespace) -> None:
        """
        Register a custom namespace handler.

        Args:
            namespace_handler (Namespace): The namespace handler instance to register.

        Raises:
            ValueError: If the provided handler is not an instance of Namespace.

        """
        if not isinstance(namespace_handler, Namespace):
            raise ValueError("Not a namespace instance.")
        namespace_handler._set_socketio(self)  # noqa: SLF001
        self.register_namespace(namespace_handler)

    def on_error(self, namespace: str = "/") -> Callable[[TExceptionHandler], TExceptionHandler]:
        """Define a custom error handler for SocketIO events.

        This decorator can be applied to a function that acts as an error
        handler for a namespace. This handler will be invoked when a SocketIO
        event handler raises an exception. The handler function must accept one
        argument, which is the exception raised. Example::

            @socketio.on_error(namespace="/chat")
            def chat_error_handler(e):
                print("An error has occurred: " + str(e))

        :param namespace: The namespace for which to register the error
                          handler. Defaults to the global namespace.
        """

        def decorator(exception_handler: TExceptionHandler) -> TExceptionHandler:
            if not callable(exception_handler):
                raise ValueError("exception_handler must be callable")
            self.config.exception_handlers[namespace] = exception_handler
            return exception_handler

        return decorator

    def on_error_default(self, exception_handler: Callable[..., Any]) -> Callable[..., Any]:
        """Define a default error handler for SocketIO events.

        This decorator can be applied to a function that acts as a default
        error handler for any namespaces that do not have a specific handler.
        Example::

            @socketio.on_error_default
            def error_handler(e):
                print("An error has occurred: " + str(e))
        """
        if not callable(exception_handler):
            raise ValueError("exception_handler must be callable")

        self.config.default_exception_handler = exception_handler
        return exception_handler

    def on_event(self, event: str, handler: Callable[..., Any], namespace: str = "/") -> None:
        """Register a SocketIO event handler.

        ``on_event`` is the non-decorator version of ``'on'``.

        Example::

            def on_foo_event(json):
                print("received json: " + str(json))


            socketio.on_event("my event", on_foo_event, namespace="/chat")

        :param message: The name of the event. This is normally a user defined
                        string, but a few event names are already defined. Use
                        ``'message'`` to define a handler that takes a string
                        payload, ``'json'`` to define a handler that takes a
                        JSON blob payload, ``'connect'`` or ``'disconnect'``
                        to create handlers for connection and disconnection
                        events.
        :param handler: The function that handles the event.
        :param namespace: The namespace on which the handler is to be
                          registered. Defaults to the global namespace.
        """
        self.on(event=event, namespace=namespace)(handler)

    async def emit(
        self,
        event: Any,
        data: Any | None = None,
        to: Any | None = None,
        room: Any | None = None,
        skip_sid: Any | None = None,
        namespace: Any | None = None,
        callback: Callable[..., Any] | None = None,
        ignore_queue: bool = False,
        *args: str | int | bool,
        **kwargs: str | int | bool,
    ) -> None:
        """Emit a server generated SocketIO event.

        This function emits a SocketIO event to one or more connected clients.
        A JSON blob can be attached to the event as payload. This function can
        be used outside of a SocketIO event context, so it is appropriate to
        use when the server is the originator of an event, outside of any
        client context, such as in a regular HTTP request handler or a
        background task. Example::

            @app.route("/ping")
            def ping():
                socketio.emit("ping event", {"data": 42}, namespace="/chat")

        :param event: The name of the user event to emit.
        :param args: A dictionary with the JSON data to send as payload.
        :param namespace: The namespace under which the message is to be sent.
                          Defaults to the global namespace.
        :param to: Send the message to all the users in the given room, or to
                   the user with the given session ID. If this parameter is not
                   included, the event is sent to all connected users.
        :param include_self: ``True`` to include the sender when broadcasting
                             or addressing a room, or ``False`` to send to
                             everyone but the sender.
        :param skip_sid: The session id of a client to ignore when broadcasting
                         or addressing a room. This is typically set to the
                         originator of the message, so that everyone except
                         that client receive the message. To skip multiple sids
                         pass a list.
        :param callback: If given, this function will be called to acknowledge
                         that the client has received the message. The
                         arguments that will be passed to the function are
                         those provided by the client. Callback functions can
                         only be used when addressing an individual client.
        """
        include_self = kwargs.pop("include_self", True)
        skip_sid = kwargs.pop("skip_sid", None)
        if not include_self and not skip_sid:
            skip_sid = request.sid

        if callback:
            # wrap the callback so that it sets app app and request contexts
            sid = None
            original_callback = callback
            original_namespace = namespace
            if has_request_context():
                sid = getattr(request, "sid", None)
                original_namespace = getattr(request, "namespace", None)

            async def _callback_wrapper(
                *args: str | int | bool, **kwargs: str | int | bool
            ) -> Coroutine[Any, Any, Any]:
                return await self._handle_event(original_callback, None, original_namespace, sid, *args, **kwargs)

            if sid:
                # the callback wrapper above will install a request context
                # before invoking the original callback
                # we only use it if the emit was issued from a Socket.IO
                # populated request context (i.e. request.sid is defined)
                callback = _callback_wrapper
        await self.server.emit(
            event=event,
            data=data,
            to=to,
            room=room,
            skip_sid=skip_sid,
            namespace=namespace,
            callback=callback,
            ignore_queue=ignore_queue,
        )

    async def call(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Emit a SocketIO event and wait for the response.

        This method issues an emit with a callback and waits for the callback
        to be invoked by the client before returning. If the callback isn’t
        invoked before the timeout, then a TimeoutError exception is raised. If
        the Socket.IO connection drops during the wait, this method still waits
        until the specified timeout. Example::

            def get_status(client, data):
                status = call("status", {"data": data}, to=client)

        :param event: The name of the user event to emit.
        :param args: A dictionary with the JSON data to send as payload.
        :param namespace: The namespace under which the message is to be sent.
                          Defaults to the global namespace.
        :param to: The session ID of the recipient client.
        :param timeout: The waiting timeout. If the timeout is reached before
                        the client acknowledges the event, then a
                        ``TimeoutError`` exception is raised. The default is 60
                        seconds.
        :param ignore_queue: Only used when a message queue is configured. If
                             set to ``True``, the event is emitted to the
                             client directly, without going through the queue.
                             This is more efficient, but only works when a
                             single server process is used, or when there is a
                             single addressee. It is recommended to always
                             leave this parameter with its default value of
                             ``False``.
        """
        namespace = kwargs.pop("namespace", "/")
        to = kwargs.pop("to", None) or kwargs.pop("room", None)
        return await self.server.call(event, *args, namespace=namespace, to=to, **kwargs)

    async def send(
        self,
        data: Any,
        json: bool = False,  # noqa: F811
        namespace: Optional[str] = None,
        to: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
        include_self: bool = True,
        skip_sid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Send a server-generated SocketIO message.

        This function sends a simple SocketIO message to one or more connected
        clients. The message can be a string or a JSON blob. This is a simpler
        version of ``emit()``, which should be preferred. This function can be
        used outside of a SocketIO event context, so it is appropriate to use
        when the server is the originator of an event.

        :param data: The message to send, either a string or a JSON blob.
        :param json: ``True`` if ``message`` is a JSON blob, ``False``
                     otherwise.
        :param namespace: The namespace under which the message is to be sent.
                          Defaults to the global namespace.
        :param to: Send the message to all the users in the given room, or to
                   the user with the given session ID. If this parameter is not
                   included, the event is sent to all connected users.
        :param include_self: ``True`` to include the sender when broadcasting
                             or addressing a room, or ``False`` to send to
                             everyone but the sender.
        :param skip_sid: The session id of a client to ignore when broadcasting
                         or addressing a room. This is typically set to the
                         originator of the message, so that everyone except
                         that client receive the message. To skip multiple sids
                         pass a list.
        :param callback: If given, this function will be called to acknowledge
                         that the client has received the message. The
                         arguments that will be passed to the function are
                         those provided by the client. Callback functions can
                         only be used when addressing an individual client.
        """
        skip_sid = request.sid if not include_self else skip_sid
        if json:
            await self.emit(
                "json",
                data,
                namespace=namespace,
                to=to,
                skip_sid=skip_sid,
                callback=callback,
                **kwargs,
            )
        else:
            await self.emit(
                "message",
                data,
                namespace=namespace,
                to=to,
                skip_sid=skip_sid,
                callback=callback,
                **kwargs,
            )

    async def close_room(self, room: str, namespace: Optional[str] = None) -> None:
        """Close a room.

        This function removes any users that are in the given room and then
        deletes the room from the server. This function can be used outside
        of a SocketIO event context.

        :param room: The name of the room to close.
        :param namespace: The namespace under which the room exists. Defaults
                          to the global namespace.
        """
        await self.server.close_room(room, namespace)

    def start_background_task(self, target: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Start a background task using the appropriate async model.

        This is a utility function that applications can use to start a
        background task using the method that is compatible with the
        selected async mode.

        :param target: the target function to execute.
        :param args: arguments to pass to the function.
        :param kwargs: keyword arguments to pass to the function.

        This function returns an object that represents the background task,
        on which the ``join()`` method can be invoked to wait for the task to
        complete.
        """
        return self.server.start_background_task(target, *args, **kwargs)

    def sleep(self, seconds: float = 0) -> None:
        """Sleep for the requested amount of time using the appropriate async model.

        This is a utility function that applications can use to put a task to
        sleep without having to worry about using the correct call for the
        selected async mode.

        """
        return self.server.sleep(seconds)

    async def send_push_promise(self, data: str, headers: Headers) -> None:
        """Empty."""
        # This method is not used in the current implementation.
        # It is a placeholder for future use if push promises are implemented.
        # The headers parameter is expected to be a werkzeug Headers object.
        # Currently, it does nothing and can be safely ignored.
        pass  # noqa: PIE790
