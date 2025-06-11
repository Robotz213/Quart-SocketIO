"""
Provide a request wrapper.

Combine functionalities from both Quart and Flask request objects.
"""

from typing import Any

from flask import Request as FlaskRequest
from quart import Request as QuartRequest


class Request(QuartRequest, FlaskRequest):
    """A request wrapper that combines Quart and Flask request functionalities."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the Request object by combining Flask and Quart request functionalities.

        Args:
            *args: Positional arguments passed to the parent classes.
            **kwargs: Keyword arguments passed to the parent classes.

        """
        from .._core import Controller

        kw = kwargs
        environ = kw.pop("environ", None)
        method = environ["REQUEST_METHOD"]
        scheme = environ["asgi.scope"].get("scheme", "http")
        path = environ["PATH_INFO"]
        query_string = environ["asgi.scope"]["query_string"]
        headers = Controller.load_headers(environ["asgi.scope"]["headers"])
        root_path = environ["asgi.scope"].get("root_path", "")
        http_version = environ["SERVER_PROTOCOL"]
        scope = environ["asgi.scope"]

        QuartRequest.__init__(
            self,
            method=method,
            scheme=scheme,
            path=path,
            query_string=query_string,
            headers=headers,
            root_path=root_path,
            http_version=http_version,
            scope=scope,
        )

        FlaskRequest.__init__(self, environ=environ)
