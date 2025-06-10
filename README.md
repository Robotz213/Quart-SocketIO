# Quart-SocketIO

Socket.IO integration for Quart applications.

> **Note:** This project is a fork of [Flask-SocketIO](https://github.com/miguelgrinberg/Flask-SocketIO), adapted to work with the [Quart](https://pgjones.gitlab.io/quart/) framework.

## Installation

You can install this package using pip:

    pip install git+https://github.com/Robotz213/Quart-SocketIO.git

> If you are using Poetry, add the package to your project with:

    poetry add git+https://github.com/Robotz213/Quart-SocketIO.git

## Example

```py
from quart import Quart, render_template
from quart_socketio import SocketIO, emit

app = Quart(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
async def index():
    return await render_template('index.html')

@socketio.event
async def my_event(message):
    await emit('my response', {'data': 'got it!'})

if __name__ == '__main__':
    socketio.run(app)
```

## Resources

- [Quart Documentation](https://quart.palletsprojects.com/en/latest/)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/en/latest/)
- [PyPI (unavailable)](#)
- Questions? See [existing questions](https://stackoverflow.com/questions/tagged/flask-socketio) on Stack Overflow, or [ask your own](https://stackoverflow.com/questions/ask?tags=python+flask-socketio+python-socketio).
