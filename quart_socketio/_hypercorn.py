from quart_socketio.common.exceptions import raise_runtime_error

type Any = any


def run_hypercorn(**kwargs: Any) -> None:
    """Run Hypercorn server with the given keyword arguments.

    This function is a wrapper around `hypercorn.run` to allow for easy integration
    with Quart-SocketIO applications.
    """
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    # Ensure that the 'app' keyword argument is provided
    if "app" not in kwargs:
        raise_runtime_error("The 'app' keyword argument must be provided.")

    app = kwargs.pop("app")
    config = Config()

    # Set default values for configuration
    config.bind = kwargs.pop("bind", [f"{kwargs.get('host', '0.0.0.0')}:{kwargs.get('port', 7000)}"])  # noqa: S104
    config.use_reloader = kwargs.pop("use_reloader", False)
    config.debug = kwargs.pop("debug", False)

    return serve(app, config)
