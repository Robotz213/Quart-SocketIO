"""
Provide a request wrapper.

Combine functionalities from both Quart and Flask request objects.
"""

from asyncio import iscoroutine
from typing import Any, Awaitable

from flask.wrappers import Request as FlaskRequest
from quart import Request as QuartRequest


class Request:
    """A request wrapper that combines Quart and Flask request functionalities."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the Request object by combining Flask and Quart request functionalities.

        Args:
            *args: Positional arguments passed to the parent classes.
            **kwargs: Keyword arguments passed to the parent classes.

        """
        from .._core import Controller

        kw = dict(kwargs)  # Create a copy to avoid modifying the original kwargs
        kwargs.clear()

        environ = kw.pop("environ", None)
        method = environ["REQUEST_METHOD"]
        scheme = environ["asgi.scope"].get("scheme", "http")
        path = environ["PATH_INFO"]
        query_string = environ["asgi.scope"]["query_string"]
        headers = Controller.load_headers(environ)
        root_path = environ["asgi.scope"].get("root_path", "")
        http_version = environ["SERVER_PROTOCOL"]
        scope = environ["asgi.scope"]

        try:
            self.quart_request = QuartRequest(
                method=method,
                scheme=scheme,
                path=path,
                query_string=query_string,
                headers=headers,
                root_path=root_path,
                http_version=http_version,
                scope=scope,
                send_push_promise=lambda *args, **kwargs: None,
            )

            self.flask_request = FlaskRequest(
                environ=environ,
            )

        except Exception as e:
            # Handle any exceptions that occur during initialization
            print(f"Error initializing QuartRequest: {e}")  # noqa: T201

    def __getattr__(self, name: str) -> Awaitable[Any] | Any:  # noqa: D105
        attr = getattr(self.flask_request, name, None) or getattr(self.quart_request, name, None)

        if iscoroutine(attr):

            async def async_wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
                return await attr(*args, **kwargs)

            return async_wrapper

        return attr

        # if callable(attr):

        #     async def async_wrapper(*args, **kwargs):
        #         if hasattr(attr, "__await__"):
        #             return await attr(*args, **kwargs)
        #         return attr(*args, **kwargs)

        #     return async_wrapper

        # if hasattr(attr, "__await__"):

        #     async def await_attr():
        #         return await attr

        #     return await_attr()

        # return attr
