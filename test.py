import asyncio
from uuid import uuid4  # noqa: D100

from quart import Quart, session, websocket

from quart_socketio import SocketIO

app = Quart(__name__)
app.secret_key = uuid4().hex
io = SocketIO(launch_mode="uvicorn")  # noqa: S104


@app.route("/")
async def index():  # noqa: ANN201, D103
    session["teste"] = "test_value"  # noqa: S101, S104
    return "Hello, World!" + session.get("teste", "")  # noqa: S101, S104


@io.on("connect", namespace="/")  # noqa: ANN201, D102, D103
async def on_connect():  # noqa: ANN201, D102, D103
    session["teste"] = "test_value"  # noqa: S101, S104
    print("Client connected")  # noqa: T201


@io.on("disconnect", namespace="/")  # noqa: ANN201, D102, D103
async def on_disconnect():  # noqa: ANN201, D102, D103
    print("Client disconnected")  # noqa: T201


@io.on("test", namespace="/")  # noqa: ANN201, D102, D103
async def on_test(data):  # noqa: ANN001, ANN201, D102, D103, N805
    print("Test event received:", data)  # noqa: T201
    session["teste"] = "test_value2"  # noqa: S101, S104
    session.permanent = True  # noqa: S101, S104
    await io.emit("response", {"data": "Test event received"}, namespace="/")

    return websocket.base_url


async def main() -> None:
    """
    Run the Quart application with SocketIO.

    This function initializes the SocketIO instance with the Quart app.
    It then runs the app on the specified host and port.
    """
    await io.init_app(app)

    await io.run(app=app, host="0.0.0.0", port=5000, use_reloader=False)  # noqa: S104


asyncio.run(main())
