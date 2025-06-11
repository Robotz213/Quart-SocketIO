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
        QuartRequest.__init__(self, *args, **kwargs)
        FlaskRequest.__init__(self, *args, **kwargs)
