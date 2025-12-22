from flask import Flask
from flask_socketio import SocketIO, emit
import paramiko
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


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
    password = data.get("password", "")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host, port=port, username=username, password=password, timeout=10
        )

        emit("ready", "Connected to SSH server")

        # Open interactive shell with proper PTY
        channel = client.invoke_shell(term="xterm-256color", width=100, height=30)
        channel.settimeout(0.0)  # Non-blocking mode

        # Send initial newline to trigger banner and prompt
        channel.send("\n")

        def read_output():
            while not channel.exit_status_ready():
                try:
                    if channel.recv_ready():
                        output = channel.recv(4096).decode("utf-8", errors="ignore")
                        if output:
                            emit("data", output)
                except Exception:
                    pass
                time.sleep(0.05)  # Small delay to avoid 100% CPU

            emit("close", "Connection closed.")

        threading.Thread(target=read_output, daemon=True).start()

        @socketio.on("input")
        def handle_input(input_data):
            if channel.send_ready():
                channel.send(input_data)

        @socketio.on("resize")
        def handle_resize(dims):
            try:
                channel.resize_pty(width=dims["cols"], height=dims["rows"])
            except Exception:
                pass

        @socketio.on("disconnect")
        def cleanup():
            channel.close()
            client.close()

    except paramiko.AuthenticationException:
        emit("error", "Authentication failed - check username/password")
    except paramiko.SSHException as e:
        emit("error", f"SSH error: {str(e)}")
    except Exception as e:
        emit("error", f"Connection error: {str(e)}")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
