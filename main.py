import asyncio

from quart import Quart

from quart_socketio import SocketIO

sio = SocketIO(allow_unsafe_werkzeug=True)


app = Quart(__name__)


async def runapp() -> None:

    async with app.app_context():
        sio.init_app(app)

    await sio.run(
        app,
        port=5000,
    )


@sio.on("connect")
def connect(*args, **kwargs):

    print(args, kwargs)
    return []


@sio.event(namespace="/bot")
async def on_listagem(*args, **kwargs):

    print(args, kwargs)
    return []


asyncio.run(runapp())
