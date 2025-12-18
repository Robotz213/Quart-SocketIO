"""Tipos do Quart-Socketio."""

from __future__ import annotations

from ._classes import Function, SocketIo
from ._config import Config, wrap_config
from ._quart import CustomJsonClass
from ._types import (
    Any,
    AsyncMode,
    Channel,
    CorsAllowOrigin,
    HypercornServer,
    Kw,
    LaunchMode,
    QueueClasses,
    QueueClassMap,
    TExceptionHandler,
    Transports,
)

__all__ = [
    "Any",
    "AsyncMode",
    "Channel",
    "Config",
    "CorsAllowOrigin",
    "CustomJsonClass",
    "Function",
    "HypercornServer",
    "Kw",
    "LaunchMode",
    "QueueClassMap",
    "QueueClasses",
    "SocketIo",
    "TExceptionHandler",
    "Transports",
    "wrap_config",
]
