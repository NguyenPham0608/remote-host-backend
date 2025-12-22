import os
import paramiko
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is running - ready for WebSocket SSH at /ws"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")

    ssh_host = os.getenv("SSH_HOST")
    ssh_port = int(os.getenv("SSH_PORT", "22"))
    ssh_user = os.getenv("SSH_USER")
    ssh_password = os.getenv("SSH_PASSWORD")

    if not all([ssh_host, ssh_user]):
        await websocket.send_text(
            "Error: Missing SSH configuration (set env vars on Render)"
        )
        await websocket.close()
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=ssh_host,
            port=ssh_port,
            username=ssh_user,
            password=ssh_password,
            timeout=10,
        )
        channel = client.invoke_shell(term="xterm-256color", width=100, height=30)
        channel.settimeout(0.0)
        channel.send("\n")  # Trigger initial banner/prompt

        while True:
            # Check for SSH output first
            if channel.recv_ready():
                output = channel.recv(4096).decode("utf-8", errors="ignore")
                if output:
                    await websocket.send_text(output)

            # Check for client input
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                if data:
                    channel.send(data)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break

    except Exception as e:
        await websocket.send_text(f"SSH Error: {str(e)}")
    finally:
        if "channel" in locals():
            channel.close()
        client.close()
        await websocket.close()
        print("SSH and WebSocket closed")
