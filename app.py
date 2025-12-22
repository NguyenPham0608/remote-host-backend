import os
import paramiko
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()


# Serve a simple health check
@app.get("/")
async def root():
    return {"message": "Backend is running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")

    # Placeholder: Replace with your Mac's details (use env vars in production!)
    ssh_host = os.getenv(
        "SSH_HOST", "your-mac-ip-or-hostname"
    )  # e.g., '192.168.1.100' or public IP
    ssh_port = int(os.getenv("SSH_PORT", 22))
    ssh_user = os.getenv("SSH_USER", "your-mac-username")
    ssh_password = os.getenv(
        "SSH_PASSWORD", "your-mac-password"
    )  # Use private_key instead for security
    # For key-based auth: ssh_private_key = paramiko.RSAKey.from_private_key_file('/path/to/private/key')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            ssh_host, port=ssh_port, username=ssh_user, password=ssh_password
        )  # Or key=ssh_private_key
        print("SSH connected")
        channel = client.invoke_shell()

        # Relay data between WebSocket and SSH channel
        while True:
            try:
                data = await websocket.receive_text()
                channel.send(data)
            except WebSocketDisconnect:
                break

            if channel.recv_ready():
                output = channel.recv(1024).decode("utf-8")
                await websocket.send_text(output)

    except Exception as e:
        await websocket.send_text(f"SSH connection error: {str(e)}")
    finally:
        channel.close()
        client.close()
        await websocket.close()
        print("Connections closed")
