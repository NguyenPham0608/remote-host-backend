import os
import paramiko
import asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI(
    title="My Web SSH Backend",
    description="WebSocket proxy for SSH access",
    version="1.0",
)


@app.get("/")
async def root():
    return {"message": "Backend is running - connect via WebSocket at /ws"}


@app.websocket("/ws")
async def websocket_ssh(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted")

    ssh_host = os.getenv("SSH_HOST")
    ssh_port = int(os.getenv("SSH_PORT", "22"))
    ssh_user = os.getenv("SSH_USER")
    ssh_password = os.getenv("SSH_PASSWORD")

    if not ssh_host or not ssh_user:
        await websocket.send_text(
            "Error: Missing SSH_HOST and SSH_USER env vars on Render"
        )
        await websocket.close()
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    channel = None
    try:
        client.connect(
            hostname=ssh_host,
            port=ssh_port,
            username=ssh_user,
            password=ssh_password,
            timeout=10,
        )
        channel = client.invoke_shell(term="xterm-256color", width=120, height=30)
        channel.settimeout(0.0)
        channel.send("\n")  # Trigger banner

        print("SSH connected")

        while True:
            if channel.recv_ready():
                data = channel.recv(4096)
                if data:
                    await websocket.send_bytes(data)

            try:
                message = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.1)
                channel.send(message)
            except asyncio.TimeoutError:
                pass
            except:
                break

    except Exception as e:
        await websocket.send_text(f"SSH Error: {str(e)}")
    finally:
        if channel:
            channel.close()
        client.close()
        try:
            await websocket.close()
        except:
            pass
        print("Connections closed")
