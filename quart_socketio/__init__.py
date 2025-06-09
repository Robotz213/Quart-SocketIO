from __future__ import annotations  # noqa: D104

import traceback
from functools import wraps
from typing import Any, AnyStr, Callable, Dict, List, Optional, TypeVar, Union

import quart
import socketio
from quart import Quart, Websocket, has_request_context, session, websocket
from quart import json as quart_json
from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError  # noqa: F401
from werkzeug.datastructures.headers import Headers

from ._manager import _ManagedSession
from ._middleare import QuartSocketIOMiddleware
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

TExceptionHandler = TypeVar("TExceptionHandler", bound=Callable[..., Any])
TFunction = TypeVar("TFunction", bound=Callable[..., Any])

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


class SocketIO:
    """
    Quart-SocketIO server for async WebSocket communication.

    Args:
        app (Quart, optional): Quart application instance. If not provided,
            call `socketio.init_app(app)` later.
        manage_session (bool, optional): If True, manages user session for
            Socket.IO events. If False, uses Quart's session management.
            Recommended True for cookie-based sessions; use False for
            server-side sessions to share session between HTTP and Socket.IO.
        message_queue (str, optional): Connection URL for a message queue
            service for multi-process communication. Not required for single
            process.
        channel (str, optional): Channel name for the message queue. If not
            specified, a default is used. Use different channels for separate
            SocketIO clusters.
        path (str, optional): Path where the Socket.IO server is exposed.
            Defaults to 'socket.io'.
        resource (str, optional): Alias for `path`.
        **kwargs: Additional Socket.IO and Engine.IO server options.

    Socket.IO server options:
        client_manager: Client manager instance. If omitted, uses in-memory
            structure.
        logger: Set True or a logger object to enable logging, False to
            disable.
        json: Alternative json module for encoding/decoding packets. Use
            `quart.json` for Quart compatibility.
        async_handlers: If True, event handlers run in separate threads. If
            False, run synchronously.
        always_connect: If False, new connections are provisional until the
            connect handler returns non-False. If True, connections are
            accepted immediately.

    Engine.IO server options:
        async_mode: Async model to use. Options: 'threading', 'eventlet',
            'gevent', 'gevent_uwsgi'. If not set, tries in order:
            'eventlet', 'gevent_uwsgi', 'gevent', 'threading'.
        ping_interval: Interval in seconds for server pings. Default: 25.
        ping_timeout: Seconds client waits for server response before
            disconnecting. Default: 5.
        max_http_buffer_size: Max message size for polling transport.
            Default: 1,000,000 bytes.
        allow_upgrades: Allow transport upgrades. Default: True.
        http_compression: Enable compression for polling transport. Default:
            True.
        compression_threshold: Only compress messages above this size
            (bytes). Default: 1024.
        cookie: Name of HTTP cookie for session id, or dict with cookie
            attributes, or None to disable.
        cors_allowed_origins: Origin(s) allowed to connect. Default: same
            origin. Use '*' to allow all.
        cors_credentials: Allow credentials (cookies, auth) in requests.
            Default: True.
        monitor_clients: If True, background task closes inactive clients.
            Default: True.
        engineio_logger: Set True or logger for Engine.IO logs, False to
            disable. Default: False.

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
            socketio.run(app)
        ```

    """

    reason: Any = socketio.AsyncServer.reason

    def __init__(self, app: Optional[Quart] = None, **kwargs: Union[str, bool, float, dict, None]) -> None:
        """
        Initialize the SocketIO server for async WebSocket communication.

        Args:
            app (Quart, optional): Quart application instance. If not provided,
                call `socketio.init_app(app)` later.
            **kwargs: Additional Socket.IO and Engine.IO server options.

        """
        self.server: Optional[socketio.AsyncServer] = None
        self.server_options: dict[str, Any] = {}
        self.asgi_server = None
        self.handlers: list[Any] = []
        self.namespace_handlers: list[Any] = kwargs.get("namespace_handlers", [])
        self.exception_handlers: dict[str, Callable[..., Any]] = {}
        self.default_exception_handler: Optional[Callable[..., Any]] = None
        self.manage_session: bool = True
        self.async_mode: str = kwargs.pop("async_mode", "asgi")
        self.launch_mode: str = kwargs.pop("launch_mode", "uvicorn")  # default to uvicorn, can be changed by the user
        self.cors_allowed_origins: Optional[Union[str, List[str], Callable[[], bool]]] = kwargs.pop(
            "cors_allowed_origins", "*"
        )
        # We can call init_app when:
        # - we were given the Flask app instance (standard initialization)
        # - we were not given the app, but we were given a message_queue
        #   (standard initialization for auxiliary process)
        # In all other cases we collect the arguments and assume the client
        # will call init_app from an app factory function.
        if app is not None or "message_queue" in kwargs:
            self.init_app(app, **kwargs)
        else:
            self.server_options.update(kwargs)

    async def init_app(self, app: Quart, **kwargs: Union[str, bool, float, dict, None]) -> None:
        """
        Initialize the SocketIO extension for the given Quart application.

        :param app: The Quart application instance to initialize with SocketIO.
        :param kwargs: Additional keyword arguments for server configuration.
        """
        if app is not None:
            if not hasattr(app, "extensions"):
                app.extensions = {}  # pragma: no cover
            app.extensions["socketio"] = self
        self.server_options.update(kwargs)
        self.manage_session = self.server_options.pop("manage_session", self.manage_session)

        if "client_manager" not in kwargs:
            url = self.server_options.get("message_queue", None)
            channel = self.server_options.pop("channel", "quart-socketio")
            write_only = app is None
            if url:
                if url.startswith(("redis://", "rediss://")):
                    queue_class = socketio.AsyncRedisManager
                elif url.startswith("kafka://"):
                    queue_class = socketio.KafkaManager
                elif url.startswith("zmq"):
                    queue_class = socketio.ZmqManager
                else:
                    queue_class = socketio.KombuManager
                queue = queue_class(url, channel=channel, write_only=write_only)
                self.server_options["client_manager"] = queue

        if "json" in self.server_options and self.server_options["json"] == quart_json:
            # quart's json module is tricky to use because its output
            # changes when it is invoked inside or outside the app context
            # so here to prevent any ambiguities we replace it with wrappers
            # that ensure that the app context is always present
            class FlaskSafeJSON:
                @staticmethod
                def dumps(*args: str | int | bool, **kwargs: str | int | bool) -> str:
                    with app.app_context():
                        return quart_json.dumps(*args, **kwargs)

                @staticmethod
                def loads(*args: str | int | bool, **kwargs: str | int | bool) -> dict[str, AnyStr | int | bool]:
                    with app.app_context():
                        return quart_json.loads(*args, **kwargs)

            self.server_options["json"] = FlaskSafeJSON

        resource = self.server_options.pop("path", None) or self.server_options.pop("resource", None) or "socket.io"
        if resource.startswith("/"):
            resource = resource[1:]

        self.server_options["async_mode"] = self.async_mode
        self.server_options["cors_allowed_origins"] = self.cors_allowed_origins

        self.server = socketio.AsyncServer(**self.server_options)
        self.async_mode = self.server.async_mode
        for handler in self.handlers:
            self.server.on(handler[0], handler[1], namespace=handler[2])
        for namespace_handler in self.namespace_handlers:
            self.server.register_namespace(namespace_handler)

        if app is not None:
            # here we attach the SocketIO middleware to the SocketIO object so
            # it can be referenced later if debug middleware needs to be
            # inserted
            self.sockio_mw = QuartSocketIOMiddleware(self.server, app, socketio_path=resource)
            app.asgi_app = self.sockio_mw

    def on(
        self, message: Union[str, int, bool], namespace: Optional[Union[str, int, bool]] = None
    ) -> Callable[[TFunction], TFunction]:
        """Register a SocketIO event handler.

        This decorator must be applied to SocketIO event handlers. Example::

            @socketio.on("my event", namespace="/chat")
            def handle_my_custom_event(json):
                print("received json: " + str(json))

        :param message: The name of the event. This is normally a user defined
                        string, but a few event names are already defined. Use
                        ``'message'`` to define a handler that takes a string
                        payload, ``'json'`` to define a handler that takes a
                        JSON blob payload, ``'connect'`` or ``'disconnect'``
                        to create handlers for connection and disconnection
                        events.
        :param namespace: The namespace on which the handler is to be
                          registered. Defaults to the global namespace.
        """
        namespace = namespace or "/"

        def decorator(handler: TFunction) -> TFunction:
            @wraps(handler)
            async def _handler(sid: str, *args: str | int | bool) -> AnyStr | int | bool:
                nonlocal namespace
                real_ns = namespace
                if namespace == "*":
                    real_ns = sid
                    sid = args[0]
                    args = args[1:]
                real_msg = message
                if message == "*":
                    real_msg = sid
                    sid = args[0]
                    args = [real_msg] + list(args[1:])
                return await self._handle_event(handler, message, real_ns, sid, *args)

            if self.server:
                self.server.on(message, _handler, namespace=namespace)
            else:
                self.handlers.append((message, _handler, namespace))
            return handler

        return decorator

    def on_error(self, namespace: Optional[str] = None) -> Callable[[TExceptionHandler], TExceptionHandler]:
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
        namespace = namespace or "/"

        def decorator(exception_handler: TExceptionHandler) -> TExceptionHandler:
            if not callable(exception_handler):
                raise ValueError("exception_handler must be callable")
            self.exception_handlers[namespace] = exception_handler
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
        self.default_exception_handler = exception_handler
        return exception_handler

    def on_event(self, message: str, handler: Callable[..., Any], namespace: Optional[str] = None) -> None:
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
        self.on(message, namespace=namespace)(handler)

    def event(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
            def set_handler(handler: Callable) -> Callable:
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
        if self.server:
            self.server.register_namespace(namespace_handler)
        else:
            self.namespace_handlers.append(namespace_handler)

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
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
        namespace = kwargs.pop("namespace", "/")
        to = kwargs.pop("to", None) or kwargs.pop("room", None)
        include_self = kwargs.pop("include_self", True)
        skip_sid = kwargs.pop("skip_sid", None)
        if not include_self and not skip_sid:
            skip_sid = websocket.sid
        callback = kwargs.pop("callback", None)
        if callback:
            # wrap the callback so that it sets app app and request contexts
            sid = None
            original_callback = callback
            original_namespace = namespace
            if has_request_context():
                sid = getattr(websocket, "sid", None)
                original_namespace = getattr(websocket, "namespace", None)

            def _callback_wrapper(*args: str | int | bool) -> object:
                return self._handle_event(original_callback, None, original_namespace, sid, *args)

            if sid:
                # the callback wrapper above will install a request context
                # before invoking the original callback
                # we only use it if the emit was issued from a Socket.IO
                # populated request context (i.e. websocket.sid is defined)
                callback = _callback_wrapper
        await self.server.emit(
            event,
            *args,
            namespace=namespace,
            to=to,
            skip_sid=skip_sid,
            callback=callback,
            **kwargs,
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
        json: bool = False,
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
        skip_sid = websocket.sid if not include_self else skip_sid
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

    async def run(self, app: Quart, host: Optional[str] = None, port: Optional[int] = None, **kwargs: Any) -> None:
        """Run the SocketIO web server.

        :param app: The Flask application instance.
        :param host: The hostname or IP address for the server to listen on.
                     Defaults to 127.0.0.1.
        :param port: The port number for the server to listen on. Defaults to
                     5000.
        :param debug: ``True`` to start the server in debug mode, ``False`` to
                      start in normal mode.
        :param use_reloader: ``True`` to enable the Flask reloader, ``False``
                             to disable it.
        :param reloader_options: A dictionary with options that are passed to
                                 the Flask reloader, such as ``extra_files``,
                                 ``reloader_type``, etc.
        :param extra_files: A list of additional files that the Flask
                            reloader should watch. Defaults to ``None``.
                            Deprecated, use ``reloader_options`` instead.
        :param log_output: If ``True``, the server logs all incoming
                           connections. If ``False`` logging is disabled.
                           Defaults to ``True`` in debug mode, ``False``
                           in normal mode. Unused when the threading async
                           mode is used.
        :param kwargs: Additional web server options. The web server options
                       are specific to the server used in each of the supported
                       async modes. Note that options provided here will
                       not be seen when using an external web server such
                       as gunicorn, since this method is not called in that
                       case.
        :param async_mode: The async mode to use for the server. This can be
                          one of "uvicorn", or "hypercorn" (Default: uvicorn).
        """
        if host is None:
            host = "127.0.0.1"
        if port is None:
            server_name = app.config["SERVER_NAME"]
            if server_name and ":" in server_name:
                port = int(server_name.rsplit(":", 1)[1])
            else:
                port = 5000

        debug: bool = kwargs.pop("debug", app.debug)
        log_output: bool = kwargs.pop("log_output", debug)  # noqa: F841
        use_reloader: bool = kwargs.pop("use_reloader", debug)  # noqa: F841
        extra_files: Optional[List[str]] = kwargs.pop("extra_files", None)
        reloader_options: Dict[str, Any] = kwargs.pop("reloader_options", {})
        if extra_files:
            reloader_options["extra_files"] = extra_files

        async_mode = kwargs.get("launch_mode", self.launch_mode)
        if async_mode not in ["uvicorn", "hypercorn"]:
            raise ValueError(f"Invalid async_mode '{async_mode}'. Supported modes are 'uvicorn' and 'hypercorn'.")

        if async_mode == "uvicorn":
            from quart_socketio._uvicorn import run_uvicorn

            await run_uvicorn(app=app, host=host, port=port, debug=debug, use_reloader=use_reloader)

        elif async_mode == "hypercorn":
            from quart_socketio._hypercorn import run_hypercorn

            await run_hypercorn(app=app, host=host, port=port, debug=debug, use_reloader=use_reloader)

    # async def stop(self) -> None:
    #     """Stop a running SocketIO web server.

    #     This method must be called from a HTTP or SocketIO handler function.

    #     """
    #     if self.server.eio.async_mode == "hypercorn":
    #         raise SystemExit
    #     elif self.server.eio.async_mode == "uvicorn":
    #         await self.asgi_server.shutdown()

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

    def test_client(
        self,
        app: Quart,
        namespace: Optional[str] = None,
        query_string: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        auth: Optional[dict[str, Any]] = None,
        quart_test_client: Any = None,
    ) -> SocketIOTestClient:
        """The Socket.IO test client is useful for testing a Flask-SocketIO server.

        It works in a similar way to the Flask Test Client, but
        adapted to the Socket.IO server.

        :param app: The Flask application instance.
        :param namespace: The namespace for the client. If not provided, the
                          client connects to the server on the global
                          namespace.
        :param query_string: A string with custom query string arguments.
        :param headers: A dictionary with custom HTTP headers.
        :param auth: Optional authentication data, given as a dictionary.
        :param quart_test_client: The instance of the Flask test client
                                  currently in use. Passing the Flask test
                                  client is optional, but is necessary if you
                                  want the Flask user session and any other
                                  cookies set in HTTP routes accessible from
                                  Socket.IO events.
        """
        return SocketIOTestClient(
            app,
            self,
            namespace=namespace,
            query_string=query_string,
            headers=headers,
            auth=auth,
            quart_test_client=quart_test_client,
        )

    async def _handle_event(
        self,
        handler: Callable[..., Any],
        message: Any,
        namespace: str,
        sid: str = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        environ = self.server.get_environ(sid, namespace=namespace)
        if not environ:
            # we don't have record of this client, ignore this event
            return "", 400
        app: Quart = self.sockio_mw.quart_app
        req = Websocket(
            path=environ["PATH_INFO"],
            query_string=environ["asgi.scope"]["query_string"],
            scheme=environ["asgi.url_scheme"],
            headers=Headers(environ["asgi.scope"]["headers"]),
            root_path=environ["asgi.scope"].get("root_path", ""),
            http_version=environ["SERVER_PROTOCOL"],
            receive=environ["asgi.receive"],
            send=environ["asgi.send"],
            subprotocols=environ["asgi.scope"].get("subprotocols", []),
            accept=environ["asgi.scope"].get("accept"),
            close=environ["asgi.scope"].get("close"),
            # method=environ["REQUEST_METHOD"],
            scope=environ["asgi.scope"],
        )

        async with app.websocket_context(req):
            if self.manage_session:
                # manage a separate session for this client's Socket.IO events
                # created as a copy of the regular user session
                if "saved_session" not in environ:
                    environ["saved_session"] = _ManagedSession(session)
                session_obj = environ["saved_session"]
                if hasattr(quart, "globals") and hasattr(quart.globals, "websocket_ctx"):
                    # update session for Flask >= 2.2
                    ctx = quart.globals.websocket_ctx._get_current_object()  # noqa: SLF001
                else:  # pragma: no cover
                    # update session for Flask < 2.2
                    ctx = quart._websocket_ctx_stack.top  # noqa: SLF001
                ctx.session = session_obj
            else:
                session_obj = session._get_current_object()  # noqa: SLF001
            websocket.sid = sid
            websocket.namespace = namespace
            websocket.event = {"message": message, "args": args}
            try:
                if message == "connect":
                    auth = args[1] if len(args) > 1 else None
                    try:
                        ret = await handler(auth)
                    except TypeError:
                        ret = await handler()
                else:
                    ret = await handler(*args)
            except SocketIOConnectionRefusedError:
                raise  # let this error bubble up to python-socketio
            except Exception as e:
                err = "".join(traceback.format_exception_only(e))

                return err
            if not self.manage_session:
                # when Flask is managing the user session, it needs to save it
                if not hasattr(session_obj, "modified") or session_obj.modified:
                    resp = app.response_class()
                    app.session_interface.save_session(app, session_obj, resp)
            return ret
