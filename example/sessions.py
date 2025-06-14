import uuid  # noqa: D100

from quart import Quart, jsonify, render_template, request, session
from quart_login import LoginManager, UserMixin, current_user, login_user, logout_user
from quart_session import Session

from quart_socketio import SocketIO, emit

app = Quart(__name__)
app.config["SECRET_KEY"] = uuid.uuid4().hex
app.config["SESSION_TYPE"] = "filesystem"
login = LoginManager(app)
Session(app)
socketio = SocketIO(app, manage_session=False)


class User(UserMixin):
    def __init__(self, id=None):
        self.id = id


@login.user_loader
def load_user(id):
    return User(id)


@app.route("/")
def index():
    return render_template("sessions.html")


@app.route("/session", methods=["GET", "POST"])
def session_access():
    if request.method == "GET":
        return jsonify({
            "session": session.get("value", ""),
            "user": current_user.id if current_user.is_authenticated else "anonymous",
        })
    data = request.get_json()
    if "session" in data:
        session["value"] = data["session"]
    elif "user" in data:
        if data["user"]:
            login_user(User(data["user"]))
        else:
            logout_user()
    return "", 204


@socketio.on("get-session")
def get_session():
    emit(
        "refresh-session",
        {
            "session": session.get("value", ""),
            "user": current_user.id if current_user.is_authenticated else "anonymous",
        },
    )


@socketio.on("set-session")
def set_session(data):
    if "session" in data:
        session["value"] = data["session"]
    elif "user" in data:
        if data["user"] is not None:
            login_user(User(data["user"]))
        else:
            logout_user()


if __name__ == "__main__":
    socketio.run(app)
