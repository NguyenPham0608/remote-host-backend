from flask import Flask, request
from flask_socketio import SocketIO, emit
import paramiko
import socket  # For error handling
import threading  # To manage streams

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow your GitHub Pages origin


@app.route("/")
def index():
    return "Backend running"


@socketio.on("connect")
def handle_connect():
    print("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


@socketio.on("connect_ssh")
def handle_connect_ssh(data):
    host = data["host"]
    port = data.get("port", 22)
    username = data["username"]
    password = data.get("password")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )  # For POC; use proper key in prod
        client.connect(host, port=port, username=username, password=password)

        emit("ready", "Connected!")

        # Open interactive shell
        channel = client.invoke_shell()

        # Thread to read output from SSH and send to client
        def read_output():
            while True:
                if channel.recv_ready():
                    output = channel.recv(1024).decode("utf-8")
                    emit("data", output)
                if channel.exit_status_ready():
                    emit("close", "Connection closed.")
                    break

        threading.Thread(target=read_output, daemon=True).start()

        # Handle input from client
        @socketio.on("input")
        def handle_input(input_data):
            channel.send(input_data)

        # Handle resize
        @socketio.on("resize")
        def handle_resize(dims):
            channel.resize_pty(width=dims["cols"], height=dims["rows"])

        # Cleanup on disconnect
        @socketio.on("disconnect")
        def cleanup():
            channel.close()
            client.close()

    except paramiko.AuthenticationException:
        emit("error", "Authentication failed")
    except paramiko.SSHException as e:
        emit("error", str(e))
    except socket.error as e:
        emit("error", f"Connection error: {str(e)}")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, allow_unsafe_werkzeug=True)
