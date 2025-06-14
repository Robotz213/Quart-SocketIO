from threading import Lock

from quart import Quart, copy_current_request_context, render_template, request, session

from quart_socketio import SocketIO, close_room, disconnect, emit, join_room, leave_room, rooms

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Quart(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, async_mode=async_mode, logger=True, engineio_logger=True)
thread = None
thread_lock = Lock()


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit("my_response", {"data": "Server generated event", "count": count})


@app.route("/")
def index():
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.event
def my_event(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": message["data"], "count": session["receive_count"]})


@socketio.event
def my_broadcast_event(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": message["data"], "count": session["receive_count"]}, broadcast=True)


@socketio.event
def join(message):
    join_room(message["room"])
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": "In rooms: " + ", ".join(rooms()), "count": session["receive_count"]})


@socketio.event
def leave(message):
    leave_room(message["room"])
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": "In rooms: " + ", ".join(rooms()), "count": session["receive_count"]})


@socketio.on("close_room")
def on_close_room(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit(
        "my_response",
        {"data": "Room " + message["room"] + " is closing.", "count": session["receive_count"]},
        to=message["room"],
    )
    close_room(message["room"])


@socketio.event
def my_room_event(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": message["data"], "count": session["receive_count"]}, to=message["room"])


@socketio.on("*")
def catch_all(event, data):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": [event, data], "count": session["receive_count"]})


@socketio.event
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    session["receive_count"] = session.get("receive_count", 0) + 1
    # for this emit we use a callback function
    # when the callback function is invoked we know that the message has been
    # received and it is safe to disconnect
    emit("my_response", {"data": "Disconnected!", "count": session["receive_count"]}, callback=can_disconnect)


@socketio.event
def my_ping():
    emit("my_pong")


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit("my_response", {"data": "Connected", "count": 0})


@socketio.on("disconnect")
def test_disconnect(reason):
    print("Client disconnected", request.sid, reason)


if __name__ == "__main__":
    socketio.run(app)
