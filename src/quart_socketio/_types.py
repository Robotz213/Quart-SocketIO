from typing import Any, Callable, List, Literal, Optional, Tuple, TypeVar, Union

import engineio
import socketio

TExceptionHandler = TypeVar("TExceptionHandler", bound=Callable[..., Any])
TFunction = TypeVar("TFunction", bound=Callable[..., Any])
TCorsAllowOrigin = Optional[Union[str, List[str], Callable[[], bool]]]
TTupleLiteral = Tuple[Literal["redis://", "rediss://", "kafka://", "zmq"]]
TQueueClass = Union[socketio.AsyncRedisManager, socketio.KafkaManager, socketio.ZmqManager, socketio.KombuManager]
TQueueClassMap = dict[TTupleLiteral, TQueueClass]


class ASyncServerType(socketio.AsyncServer):
    """
    Type extension for socketio.AsyncServer with an explicit engineio.AsyncServer attribute.

    Inherits from socketio.AsyncServer and adds a type annotation for the 'eio' attribute,
    which represents the underlying Engine.IO AsyncServer instance.
    """

    eio: engineio.AsyncServer


class CustomJsonClass:
    def __init__(self) -> None:
        """Initialize the CustomJsonClass."""
        raise NotImplementedError(
            "CustomJsonClass must be subclassed and initialized with a custom JSON implementation"
        )

    def dumps(self, obj: Any) -> str:
        raise NotImplementedError("CustomJsonClass must implement dumps method")

    def loads(self, s: str) -> Any:
        raise NotImplementedError("CustomJsonClass must implement loads method")
