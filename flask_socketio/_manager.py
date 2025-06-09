from quart.sessions import SessionMixin


class _ManagedSession(dict, SessionMixin):
    """Manage user sessions for Flask-SocketIO.

    User sessions are stored as a simple dict, expanded with the Flask session
    attributes.
    """
