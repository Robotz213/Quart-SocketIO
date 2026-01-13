import quart
from quart.sessions import SessionMixin


class _ManagedSession(dict, SessionMixin):
    """Manage user sessions for Quart-SocketIO.

    User sessions are stored as a simple dict, expanded with the Quart session
    attributes.
    """


def get_session_manager(
    environ: dict,
    session: SessionMixin,
) -> _ManagedSession:
    # manage a separate session for this client's Socket.IO events
    # created as a copy of the regular user session
    if "saved_session" not in environ:
        environ["saved_session"] = _ManagedSession(session)
    session_obj = environ["saved_session"]
    if hasattr(quart, "globals") and hasattr(quart.globals, "websocket_ctx"):
        # update session for Quart >= 2.2
        ctx = quart.globals.websocket_ctx._get_current_object()  # noqa: SLF001
    else:  # pragma: no cover
        # update session for Quart < 2.2
        ctx = quart._websocket_ctx_stack.top  # noqa: SLF001
    ctx.session = session_obj

    return session_obj
