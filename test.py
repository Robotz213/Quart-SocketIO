import asyncio  # noqa: D100

from quart import Quart, request

import quart_socketio
from quart_socketio import SocketIO

app = Quart(__name__)


@app.route("/")
async def index():  # noqa: ANN201, D103
    return "Hello, World!"


class TestNamespace(quart_socketio.Namespace):
    """
    Custom namespace for handling SocketIO events.

    This class extends the `quart_socketio.Namespace` class to define custom event handlers
    for the SocketIO server. It can be used to handle specific events in a dedicated namespace.
    """

    def is_asyncio_based(self):  # noqa: ANN201, D102, D103
        """
        Check if the namespace is based on asyncio.

        This method is used to determine if the namespace is using asyncio for its operations.
        It returns True, indicating that this namespace is asyncio-based.
        """
        return True

    async def on_connect(self):  # noqa: ANN201, D102, D103
        print(request.headers)  # noqa: T201
        print("Client connected")  # noqa: T201

    async def on_disconnect(self):  # noqa: ANN201, D102, D103
        print("Client disconnected")  # noqa: T201

    async def on_test(self, data):  # noqa: ANN001, ANN201, D102, D103, N805
        print("Test event received:", data)  # noqa: T201


io = SocketIO(launch_mode="uvicorn", namespace_handlers=[TestNamespace("/")])  # noqa: S104


async def main() -> None:
    """
    Run the Quart application with SocketIO.

    This function initializes the SocketIO instance with the Quart app.
    It then runs the app on the specified host and port.
    """
    await io.init_app(app)

    await io.run(app=app, host="0.0.0.0", port=5000, use_reloader=False)  # noqa: S104


asyncio.run(main())
