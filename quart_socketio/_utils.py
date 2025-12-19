from __future__ import annotations

from typing import TYPE_CHECKING

from quart import current_app, request

if TYPE_CHECKING:
    from quart_socketio import SocketIO


type Any = any


async def emit(event: str, *args: Any, **kwargs: Any) -> None:
    """Emit a SocketIO event.

    This function emits a SocketIO event to one or more connected clients. A
    JSON blob can be attached to the event as payload. This is a function that
    can only be called from a SocketIO event handler, as in obtains some
    information from the current client context. Example::

        @socketio.on("my event")
        def handle_my_custom_event(json):
            emit("my response", {"data": 42})

    :param event: The name of the user event to emit.
    :param args: A dictionary with the JSON data to send as payload.
    :param namespace: The namespace under which the message is to be sent.
                      Defaults to the namespace used by the originating event.
                      A ``'/'`` can be used to explicitly specify the global
                      namespace.
    :param callback: Callback function to invoke with the client's
                     acknowledgement.
    :param broadcast: ``True`` to send the message to all clients, or ``False``
                      to only reply to the sender of the originating event.
    :param to: Send the message to all the users in the given room, or to the
               user with the given session ID. If this argument is not set and
               ``broadcast`` is ``False``, then the message is sent only to the
               originating user.
    :param include_self: ``True`` to include the sender when broadcasting or
                         addressing a room, or ``False`` to send to everyone
                         but the sender.
    :param skip_sid: The session id of a client to ignore when broadcasting
                     or addressing a room. This is typically set to the
                     originator of the message, so that everyone except
                     that client receive the message. To skip multiple sids
                     pass a list.
    :param ignore_queue: Only used when a message queue is configured. If
                         set to ``True``, the event is emitted to the
                         clients directly, without going through the queue.
                         This is more efficient, but only works when a
                         single server process is used, or when there is a
                         single addressee. It is recommended to always leave
                         this parameter with its default value of ``False``.
    """
    namespace = kwargs.get("namespace", request.namespace)
    callback = kwargs.get("callback")
    broadcast = kwargs.get("broadcast")
    to = kwargs.pop("to", None) or kwargs.pop("room", None)
    if to is None and not broadcast:
        to = request.sid
    include_self = kwargs.get("include_self", True)
    skip_sid = kwargs.get("skip_sid")
    ignore_queue = kwargs.get("ignore_queue", False)

    socketio: SocketIO = current_app.extensions["socketio"]
    return await socketio.emit(
        event,
        *args,
        namespace=namespace,
        to=to,
        include_self=include_self,
        skip_sid=skip_sid,
        callback=callback,
        ignore_queue=ignore_queue,
    )


async def call(event: str, *args: Any, **kwargs: Any) -> Any:
    """Emit a SocketIO event and wait for the response.

    This function issues an emit with a callback and waits for the callback to
    be invoked by the client before returning. If the callback isn’t invoked
    before the timeout, then a TimeoutError exception is raised. If the
    Socket.IO connection drops during the wait, this method still waits until
    the specified timeout. Example::

        def get_status(client, data):
            status = call("status", {"data": data}, to=client)

    :param event: The name of the user event to emit.
    :param args: A dictionary with the JSON data to send as payload.
    :param namespace: The namespace under which the message is to be sent.
                      Defaults to the namespace used by the originating event.
                      A ``'/'`` can be used to explicitly specify the global
                      namespace.
    :param to: The session ID of the recipient client. If this argument is not
               given, the event is sent to the originating client.
    :param timeout: The waiting timeout. If the timeout is reached before the
                    client acknowledges the event, then a ``TimeoutError``
                    exception is raised. The default is 60 seconds.
    :param ignore_queue: Only used when a message queue is configured. If
                         set to ``True``, the event is emitted to the
                         client directly, without going through the queue.
                         This is more efficient, but only works when a
                         single server process is used, or when there is a
                         single addressee. It is recommended to always leave
                         this parameter with its default value of ``False``.
    """  # noqa: RUF002
    namespace = kwargs.get("namespace", request.namespace)
    to = kwargs.pop("to", None) or kwargs.pop("room", None)
    if to is None:
        to = request.sid
    timeout = kwargs.get("timeout", 60)
    ignore_queue = kwargs.get("ignore_queue", False)

    socketio: SocketIO = current_app.extensions["socketio"]
    return await socketio.call(
        event,
        *args,
        namespace=namespace,
        to=to,
        ignore_queue=ignore_queue,
        timeout=timeout,
    )


async def send(message: Any, **kwargs: Any) -> None:
    """Send a SocketIO message.

    This function sends a simple SocketIO message to one or more connected
    clients. The message can be a string or a JSON blob. This is a simpler
    version of ``emit()``, which should be preferred. This is a function that
    can only be called from a SocketIO event handler.

    :param message: The message to send, either a string or a JSON blob.
    :param json: ``True`` if ``message`` is a JSON blob, ``False``
                     otherwise.
    :param namespace: The namespace under which the message is to be sent.
                      Defaults to the namespace used by the originating event.
                      An empty string can be used to use the global namespace.
    :param callback: Callback function to invoke with the client's
                     acknowledgement.
    :param broadcast: ``True`` to send the message to all connected clients, or
                      ``False`` to only reply to the sender of the originating
                      event.
    :param to: Send the message to all the users in the given room, or to the
               user with the given session ID. If this argument is not set and
               ``broadcast`` is ``False``, then the message is sent only to the
               originating user.
    :param include_self: ``True`` to include the sender when broadcasting or
                         addressing a room, or ``False`` to send to everyone
                         but the sender.
    :param skip_sid: The session id of a client to ignore when broadcasting
                     or addressing a room. This is typically set to the
                     originator of the message, so that everyone except
                     that client receive the message. To skip multiple sids
                     pass a list.
    :param ignore_queue: Only used when a message queue is configured. If
                         set to ``True``, the event is emitted to the
                         clients diretamente, sem passar pela fila.
                         Isso é mais eficiente, mas só funciona quando um
                         único processo de servidor é usado, ou quando há um
                         único destinatário. É recomendável deixar sempre este
                         parâmetro com seu valor padrão ``False``.
    """
    json = kwargs.get("json", False)
    namespace = kwargs.get("namespace", request.namespace)
    callback = kwargs.get("callback")
    broadcast = kwargs.get("broadcast")
    to = kwargs.pop("to", None) or kwargs.pop("room", None)
    if to is None and not broadcast:
        to = request.sid
    include_self = kwargs.get("include_self", True)
    skip_sid = kwargs.get("skip_sid")
    ignore_queue = kwargs.get("ignore_queue", False)

    socketio: SocketIO = current_app.extensions["socketio"]
    return await socketio.send(
        message,
        json=json,
        namespace=namespace,
        to=to,
        include_self=include_self,
        skip_sid=skip_sid,
        callback=callback,
        ignore_queue=ignore_queue,
    )


async def join_room(
    room: str,
    sid: str | None = None,
    namespace: str | None = None,
) -> None:
    """Join a room.

    This function puts the user in a room, under the current namespace. The
    user and the namespace are obtained from the event context. This is a
    function that can only be called from a SocketIO event handler. Example::

        @socketio.on("join")
        def on_join(data):
            username = session["username"]
            room = data["room"]
            join_room(room)
            send(username + " has entered the room.", to=room)

    :param room: The name of the room to join.
    :param sid: The session id of the client. If not provided, the client is
                obtained from the request context.
    :param namespace: The namespace for the room. If not provided, the
                      namespace is obtained from the request context.
    """
    socketio: SocketIO = current_app.extensions["socketio"]
    sid = sid or request.sid
    namespace = namespace or request.namespace
    await socketio.server.enter_room(sid, room, namespace=namespace)


async def leave_room(
    room: str,
    sid: str | None = None,
    namespace: str | None = None,
) -> None:
    """Leave a room.

    This function removes the user from a room, under the current namespace.
    The user and the namespace are obtained from the event context. Example::

        @socketio.on("leave")
        def on_leave(data):
            username = session["username"]
            room = data["room"]
            leave_room(room)
            send(username + " has left the room.", to=room)

    :param room: The name of the room to leave.
    :param sid: The session id of the client. If not provided, the client is
                obtained from the request context.
    :param namespace: The namespace for the room. If not provided, the
                      namespace is obtained from the request context.
    """
    socketio: SocketIO = current_app.extensions["socketio"]
    sid = sid or request.sid
    namespace = namespace or request.namespace
    await socketio.server.leave_room(sid, room, namespace=namespace)


async def close_room(room: str, namespace: str | None = None) -> None:
    """Close a room.

    This function removes any users that are in the given room and then deletes
    the room from the server.

    :param room: The name of the room to close.
    :param namespace: The namespace for the room. If not provided, the
                      namespace is obtained from the request context.
    """
    socketio: SocketIO = current_app.extensions["socketio"]
    namespace = namespace or request.namespace
    await socketio.server.close_room(room, namespace=namespace)


def rooms(
    sid: str | None = None,
    namespace: str | None = None,
) -> list[str]:
    """Return a list of the rooms the client is in.

    This function returns all the rooms the client has entered, including its
    own room, assigned by the Socket.IO server.

    :param sid: The session id of the client. If not provided, the client is
                obtained from the request context.
    :param namespace: The namespace for the room. If not provided, the
                      namespace is obtained from the request context.
    """
    socketio: SocketIO = current_app.extensions["socketio"]
    sid = sid or request.sid
    namespace = namespace or request.namespace
    return socketio.server.rooms(sid, namespace=namespace)


async def disconnect(
    sid: str | None = None,
    namespace: str | None = None,
    *,
    silent: bool = False,
) -> Any:
    """Disconnect the client.

    This function terminates the connection with the client. As a result of
    this call the client will receive a disconnect event. Example::

        @socketio.on('message')
        def receive_message(msg):
            if is_banned(session['username']):
                disconnect()
            else:
                # ...

    :param sid: The session id of the client. If not provided, the client is
                obtained from the request context.
    :param namespace: The namespace for the room. If not provided, the
                      namespace is obtained from the request context.
    :param silent: this option is deprecated.
    """
    socketio: SocketIO = current_app.extensions["socketio"]
    sid = sid or request.sid
    namespace = namespace or request.namespace
    return await socketio.server.disconnect(sid, namespace=namespace)
