from __future__ import annotations

import io
from mimetypes import guess_extension
from typing import IO, TYPE_CHECKING, Any, Optional, Tuple, TypedDict
from uuid import uuid4

from magic import Magic
from quart import current_app, request
from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.test import EnvironBuilder

if TYPE_CHECKING:
    from quart_socketio import SocketIO


class FilesRequestData(TypedDict):
    filename: str
    file: IO[bytes]
    content_type: str
    content_length: int


async def _generate_filename(typefile: str) -> str:
    return f"{uuid4().hex[:10]}{guess_extension(typefile)}"


async def _construct_file_object(stream: IO, filename: str, content_type: str, content_length: int) -> FilesRequestData:
    return FilesRequestData(
        file=stream,
        filename=filename,
        content_type=content_type,
        content_length=content_length,
    )


async def _constructor_from_bytes(
    content: bytes | bytearray, name: str | None = None
) -> None | Tuple[str | FileStorage]:
    content_type = Magic(mime=True).from_buffer(content)
    if content_type == "application/octet-stream":
        return None
    stream = io.BytesIO(content)
    content_length = len(content)
    filename = name if name else await _generate_filename(content_type)
    return await _get_file(
        await _construct_file_object(
            stream=stream,
            filename=filename,
            content_type=content_type,
            content_length=content_length,
        )
    )


async def _get_file(data: FilesRequestData) -> Tuple[str | FileStorage]:
    content = FileStorage(
        stream=data["file"],
        filename=data["filename"],
        name=data["filename"],
        content_type=data["content_type"],
        content_length=data["content_length"],
    )

    return data["filename"], content


async def _handle_files(
    k: str | None = None, v: dict | bytes | bytearray | None = None
) -> Tuple[str | FileStorage] | None:
    if isinstance(v, (bytes, bytearray)):
        _file = await _constructor_from_bytes(name=k, content=v)
        if _file:
            return _file

    elif isinstance(v, dict):
        content_type = v.get("content_type")
        filename = str(v.get("name", v.get("filename", await _generate_filename(content_type))))
        filter_content_byte = list(filter(lambda x: isinstance(x[1], (bytes, bytearray)), list(v.values())))
        if len(filter_content_byte) == 0:
            return

        content_byte = filter_content_byte[-1]

        if not content_type or content_type == "application/octet-stream":
            _file = await _constructor_from_bytes(name=filename, content=content_byte)
            if _file:
                return _file

            return

        content_length = int(v.get("content_length", len(content_byte)))
        file_data = FilesRequestData(
            file=io.BytesIO(content_byte),
            filename=filename,
            content_type=content_type,
            content_length=content_length,
        )

        return await _get_file(file_data)


async def parse_provided_data(data: dict) -> Tuple[MultiDict, MultiDict]:
    """Tratamento de informações recebidas no emit."""
    new_data = MultiDict()
    new_files = MultiDict()
    data_refs = ["json", "data", "form"]
    for k, v in list(data.items()):
        if isinstance(v, (bytes, bytearray)) or (k.lower() == "files" or k.lower() == "file"):
            _file = await _handle_files(k=k, v=v)
            if _file:
                new_files.add(_file[0], _file[1])

        elif any(k.lower() == dataref for dataref in data_refs):
            if isinstance(v, (list, dict)):
                if isinstance(v, dict):
                    for key, value in list(v.items()):
                        if isinstance(value, (bytes, bytearray)):
                            _file_from_dict = await _handle_files(k=key, v=value)
                            if _file_from_dict:
                                new_files.add(_file[0], _file[1])

                            continue
                        new_data.add(key, value)

                    continue

                elif isinstance(v, list):
                    for pos, item in enumerate(v):
                        if isinstance(item, (bytes, bytearray)):
                            _file_from_list = await _handle_files(v=item)
                            if _file_from_list:
                                new_files.add(_file[0], _file[1])

                            continue

                        new_data.add(f"item{pos}", item)

                    continue

            new_data.add(k, v)

    return [new_data, new_files]


async def encode_data_as_form(data: MultiDict) -> tuple[bytes, str]:
    # x-www-form-urlencoded
    builder = EnvironBuilder(method="POST", data=data)

    env = builder.get_environ()
    content_length = int(env["CONTENT_LENGTH"])
    body = env["wsgi.input"].read(content_length)
    content_type = env["CONTENT_TYPE"]

    return body, content_type


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
    if "namespace" in kwargs:
        namespace = kwargs["namespace"]
    else:
        namespace = request.namespace
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
    """
    if "namespace" in kwargs:
        namespace = kwargs["namespace"]
    else:
        namespace = request.namespace
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
    if "namespace" in kwargs:
        namespace = kwargs["namespace"]
    else:
        namespace = request.namespace
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


async def join_room(room: str, sid: Optional[str] = None, namespace: Optional[str] = None) -> None:
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


async def leave_room(room: str, sid: Optional[str] = None, namespace: Optional[str] = None) -> None:
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


async def close_room(room: str, namespace: Optional[str] = None) -> None:
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


async def rooms(sid: Optional[str] = None, namespace: Optional[str] = None) -> list[str]:
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


async def disconnect(sid: Optional[str] = None, namespace: Optional[str] = None, silent: bool = False) -> Any:
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
