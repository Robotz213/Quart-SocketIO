from typing import Any, Callable, List, Literal, Optional, Tuple, TypeVar, Union

import socketio

TExceptionHandler = TypeVar("TExceptionHandler", bound=Callable[..., Any])
TFunction = TypeVar("TFunction", bound=Callable[..., Any])
TCorsAllowOrigin = Optional[Union[str, List[str], Callable[[], bool]]]
TTupleLiteral = Tuple[Literal["redis://", "rediss://", "kafka://", "zmq"]]
TQueueClass = Union[socketio.AsyncRedisManager, socketio.KafkaManager, socketio.ZmqManager, socketio.KombuManager]
TQueueClassMap = dict[TTupleLiteral, TQueueClass]
