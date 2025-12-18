from typing import Protocol


class CustomJsonClass(Protocol):
    @staticmethod
    def dump(
        obj,  # noqa: ANN001
        fp,  # noqa: ANN001
        *,
        skipkeys=False,  # noqa: ANN001
        ensure_ascii=True,  # noqa: ANN001
        check_circular=True,  # noqa: ANN001
        allow_nan=True,  # noqa: ANN001
        cls=None,  # noqa: ANN001
        indent=None,  # noqa: ANN001
        separators=None,  # noqa: ANN001
        default=None,  # noqa: ANN001
        sort_keys=False,  # noqa: ANN001
        **kw,  # noqa: ANN003
    ) -> str:
        """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a ``.write()``-supporting file-like object).

        If ``skipkeys`` is true then ``dict`` keys that are not basic types
        (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped
        instead of raising a ``TypeError``.

        If ``ensure_ascii`` is false, then the strings written to ``fp`` can
        contain non-ASCII characters if they appear in strings contained in
        ``obj``. Otherwise, all such characters are escaped in JSON strings.

        If ``check_circular`` is false, then the circular reference check
        for container types will be skipped and a circular reference will
        result in an ``RecursionError`` (or worse).

        If ``allow_nan`` is false, then it will be a ``ValueError`` to
        serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``)
        in strict compliance of the JSON specification, instead of using the
        JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).

        If ``indent`` is a non-negative integer, then JSON array elements and
        object members will be pretty-printed with that indent level. An indent
        level of 0 will only insert newlines. ``None`` is the most compact
        representation.

        If specified, ``separators`` should be an ``(item_separator, key_separator)``
        tuple.  The default is ``(', ', ': ')`` if *indent* is ``None`` and
        ``(',', ': ')`` otherwise.  To get the most compact JSON representation,
        you should specify ``(',', ':')`` to eliminate whitespace.

        ``default(obj)`` is a function that should return a serializable version
        of obj or raise TypeError. The default simply raises TypeError.

        If *sort_keys* is true (default: ``False``), then the output of
        dictionaries will be sorted by key.

        To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the
        ``.default()`` method to serialize additional types), specify it with
        the ``cls`` kwarg; otherwise ``JSONEncoder`` is used.

        """  # noqa: E501

    @staticmethod
    def dumps(
        obj,  # noqa: ANN001
        *,
        skipkeys=False,  # noqa: ANN001
        ensure_ascii=True,  # noqa: ANN001
        check_circular=True,  # noqa: ANN001
        allow_nan=True,  # noqa: ANN001
        cls=None,  # noqa: ANN001
        indent=None,  # noqa: ANN001
        separators=None,  # noqa: ANN001
        default=None,  # noqa: ANN001
        sort_keys=False,  # noqa: ANN001
        **kw,  # noqa: ANN003
    ) -> str:
        """Serialize ``obj`` to a JSON formatted ``str``.

        If ``skipkeys`` is true then ``dict`` keys that are not basic types
        (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped
        instead of raising a ``TypeError``.

        If ``ensure_ascii`` is false, then the return value can contain non-ASCII
        characters if they appear in strings contained in ``obj``. Otherwise, all
        such characters are escaped in JSON strings.

        If ``check_circular`` is false, then the circular reference check
        for container types will be skipped and a circular reference will
        result in an ``RecursionError`` (or worse).

        If ``allow_nan`` is false, then it will be a ``ValueError`` to
        serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``) in
        strict compliance of the JSON specification, instead of using the
        JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).

        If ``indent`` is a non-negative integer, then JSON array elements and
        object members will be pretty-printed with that indent level. An indent
        level of 0 will only insert newlines. ``None`` is the most compact
        representation.

        If specified, ``separators`` should be an ``(item_separator, key_separator)``
        tuple.  The default is ``(', ', ': ')`` if *indent* is ``None`` and
        ``(',', ': ')`` otherwise.  To get the most compact JSON representation,
        you should specify ``(',', ':')`` to eliminate whitespace.

        ``default(obj)`` is a function that should return a serializable version
        of obj or raise TypeError. The default simply raises TypeError.

        If *sort_keys* is true (default: ``False``), then the output of
        dictionaries will be sorted by key.

        To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the
        ``.default()`` method to serialize additional types), specify it with
        the ``cls`` kwarg; otherwise ``JSONEncoder`` is used.

        """  # noqa: E501

    @staticmethod
    def load[T](
        fp,  # noqa: ANN001
        *,
        cls=None,  # noqa: ANN001
        object_hook=None,  # noqa: ANN001
        parse_float=None,  # noqa: ANN001
        parse_int=None,  # noqa: ANN001
        parse_constant=None,  # noqa: ANN001
        object_pairs_hook=None,  # noqa: ANN001
        **kw,  # noqa: ANN003
    ) -> T:
        """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing a JSON document) to a Python object.

        ``object_hook`` is an optional function that will be called with the
        result of any object literal decode (a ``dict``). The return value of
        ``object_hook`` will be used instead of the ``dict``. This feature
        can be used to implement custom decoders (e.g. JSON-RPC class hinting).

        ``object_pairs_hook`` is an optional function that will be called with the
        result of any object literal decoded with an ordered list of pairs.  The
        return value of ``object_pairs_hook`` will be used instead of the ``dict``.
        This feature can be used to implement custom decoders.  If ``object_hook``
        is also defined, the ``object_pairs_hook`` takes priority.

        To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``
        kwarg; otherwise ``JSONDecoder`` is used.
        """  # noqa: E501

    @staticmethod
    def loads[T](
        s,  # noqa: ANN001
        *,
        cls=None,  # noqa: ANN001
        object_hook=None,  # noqa: ANN001
        parse_float=None,  # noqa: ANN001
        parse_int=None,  # noqa: ANN001
        parse_constant=None,  # noqa: ANN001
        object_pairs_hook=None,  # noqa: ANN001
        **kw,  # noqa: ANN003
    ) -> T:
        """Deserialize ``s`` (a ``str``, ``bytes`` or ``bytearray`` instance containing a JSON document) to a object.

        ``object_hook`` is an optional function that will be called with the
        result of any object literal decode (a ``dict``). The return value of
        ``object_hook`` will be used instead of the ``dict``. This feature
        can be used to implement custom decoders (e.g. JSON-RPC class hinting).

        ``object_pairs_hook`` is an optional function that will be called with the
        result of any object literal decoded with an ordered list of pairs.  The
        return value of ``object_pairs_hook`` will be used instead of the ``dict``.
        This feature can be used to implement custom decoders.  If ``object_hook``
        is also defined, the ``object_pairs_hook`` takes priority.

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.

        To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``
        kwarg; otherwise ``JSONDecoder`` is used.
        """  # noqa: E501
