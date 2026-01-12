import asyncio
from contextlib import suppress

from quart import Quart, Response, jsonify

from quart_socketio import SocketIO

sio = SocketIO(allow_unsafe_werkzeug=True)


app = Quart(__name__)


async def runapp() -> None:

    async with app.app_context():
        sio.init_app(app)

    await sio.run(
        app,
        port=5001,
    )


@sio.on("connect")
async def connect(*args, **kwargs) -> None:
    print("Client connected!")


@app.route("/start")
async def start() -> Response:

    return jsonify({"status": "started"})


with suppress(KeyboardInterrupt):
    asyncio.run(runapp())
