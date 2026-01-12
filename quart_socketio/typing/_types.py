from collections.abc import Callable
from typing import Literal, ParamSpec

from socketio import AsyncRedisManager, KafkaManager, KombuManager, ZmqManager

P = ParamSpec("P")
type AsyncMode = Literal["aiohttp", "sanic", "tornado", "asgi"]
type Transports = list[Literal["polling", "websocket"]]
type LaunchMode = Literal["uvicorn", "hypercorn"]
type Any = any


type Kw[T] = str | bool | Any | T
type CorsAllowOrigin = str | list[str] | Callable[[], bool] | None
type RedisURLPrefix = tuple[Literal["redis://", "rediss://"]]
type KafkaURLPrefix = tuple[Literal["kafka://"]]
type ZmqURLPrefix = tuple[Literal["zmq"]]
type TupleLiteral = tuple[RedisURLPrefix, KafkaURLPrefix, ZmqURLPrefix]
type QueueClasses = type[
    AsyncRedisManager | KafkaManager | ZmqManager | KombuManager
]
type HypercornServer = object
type QueueClassMap = dict[TupleLiteral, QueueClasses]
type TExceptionHandler[T] = Callable[P, T]
type Channel = Literal["quart-socketio"]
