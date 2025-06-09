import asyncio  # noqa: D100

from quart import Quart, request, websocket

import quart_socketio
from quart_socketio import SocketIO

app = Quart(__name__)

io = SocketIO(launch_mode="uvicorn")  # noqa: S104


@app.route("/")
async def index():  # noqa: ANN201, D103
    return "Hello, World!"


@io.on("connect", namespace="/")  # noqa: ANN201, D102, D103
def on_connect():  # noqa: ANN201, D102, D103
    print(websocket.headers)  # noqa: T201
    print("Client connected")  # noqa: T201


@io.on("disconnect", namespace="/")  # noqa: ANN201, D102, D103
def on_disconnect():  # noqa: ANN201, D102, D103
    print("Client disconnected")  # noqa: T201


@io.on("test", namespace="/")  # noqa: ANN201, D102, D103
def on_test(data):  # noqa: ANN001, ANN201, D102, D103, N805
    print("Test event received:", data)  # noqa: T201
    io.emit("response", {"data": "Test event received"}, namespace="/")


async def main() -> None:
    """
    Run the Quart application with SocketIO.

    This function initializes the SocketIO instance with the Quart app.
    It then runs the app on the specified host and port.
    """
    await io.init_app(app)

    await io.run(app=app, host="0.0.0.0", port=5000, use_reloader=False)  # noqa: S104


asyncio.run(main())
