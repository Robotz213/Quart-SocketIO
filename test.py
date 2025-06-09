import asyncio  # noqa: D100

from quart import Quart, request

from quart_socketio import SocketIO

io = SocketIO(launch_mode="uvicorn")
app = Quart(__name__)


async def main() -> None:
    """
    Run the Quart application with SocketIO.

    This function initializes the SocketIO instance with the Quart app.
    It then runs the app on the specified host and port.
    """
    io.init_app(app)

    await io.run(app=app, host="0.0.0.0", port=5000, use_reloader=False)  # noqa: S104


@app.route("/")
async def index():  # noqa: ANN201, D103
    return "Hello, World!"


@io.on("connect")
async def handle_connect():  # noqa: ANN201, D103
    print(request.headers)  # noqa: T201
    print("Client connected")  # noqa: T201


@io.on("disconnect")
async def handle_disconnect():  # noqa: ANN201, D103
    print("Client disconnected")  # noqa: T201


@io.on("test")
async def handle_test(data):  # noqa: ANN001, ANN201, D103
    print("Test event received:", data)  # noqa: T201


asyncio.run(main())
