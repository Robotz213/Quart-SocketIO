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

    server = uvicorn.Server(uvicorn.Config(app, host=host, port=7000, log_level=log_level, log_config=log_config))

    return await server.serve()
