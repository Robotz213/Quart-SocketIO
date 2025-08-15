from __future__ import annotations

from typing import Any

import uvicorn


async def run_uvicorn(**kwargs: Any) -> uvicorn.Server:
    """Run Uvicorn server with the given keyword arguments.

    This function is a wrapper around `uvicorn.run` to allow for easy integration
    with Quart-SocketIO applications.
    """
    import uvicorn

    # Ensure that the 'app' keyword argument is provided
    if "app" not in kwargs:
        raise ValueError("The 'app' keyword argument must be provided.")

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
        loop="uvloop",
        ws="wsproto",
        backlog=65535,
        workers=8,
        timeout_keep_alive=75,
        limit_concurrency=10_000,
        interface="asgi3",
        lifespan="on",
    )
    server = uvicorn.Server(config)

    return await server.serve()
