from __future__ import annotations

from typing import TYPE_CHECKING

from quart_socketio.common.exceptions import raise_value_error

if TYPE_CHECKING:
    from uvicorn import Server

    from quart_socketio.typing import Kw


async def run_uvicorn(**kwargs: Kw) -> Server:
    """Run Uvicorn server with the given keyword arguments.

    This function is a wrapper around `uvicorn.run`
    to allow for easy integration
    with Quart-SocketIO applications.
    """
    import uvicorn

    # Ensure that the 'app' keyword argument is provided
    if "app" not in kwargs:
        raise_value_error("The 'app' keyword argument must be provided.")

    app = kwargs.pop("app")
    log_config = kwargs.pop("log_config", None)
    log_level = kwargs.pop("log_level", "info")
    host = kwargs.pop("host", "0.0.0.0")  # noqa: S104
    port = kwargs.pop("port", 7000)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        log_config=log_config,
    )
    server = uvicorn.Server(config)

    return await server.serve()
