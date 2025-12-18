# noqa: D100

from __future__ import annotations

from typing import NoReturn

type Any = any


class QuartTypeError(TypeError):  # noqa: D101
    def __init__(self, message: str, *args: Any) -> None:  # noqa: D107
        super().__init__(*args)


class QuartValueError(ValueError):  # noqa: D101
    def __init__(self, message: str, *args: Any) -> None:  # noqa: D107
        super().__init__(*args)


class QuartRuntimeError(RuntimeError):  # noqa: D101
    def __init__(self, message: str, *args: Any) -> None:  # noqa: D107
        super().__init__(*args)


class QuartSocketioError(Exception):  # noqa: D101
    def __init__(self, exc: Exception, *args: Any) -> None:  # noqa: D107

        super().__init__(*args)


def raise_runtime_error(message: str) -> NoReturn:  # noqa: D103
    raise QuartTypeError(message=message)


def raise_value_error(message: str) -> NoReturn:  # noqa: D103
    raise QuartTypeError(message=message)


def raise_type_error(message: str) -> NoReturn:  # noqa: D103
    raise QuartTypeError(message=message)
