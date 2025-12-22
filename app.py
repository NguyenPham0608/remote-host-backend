import os
import paramiko
import asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI(
    title="My Web SSH Backend",
    description="Secure WebSocket proxy for SSH",
    version="1.0",
)


@app.get("/")
def root():
    return {"message": "Backend is running - connect via WebSocket at /ws"}


@app.websocket("/ws")
async def ssh_websocket(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established")

    ssh_host = os.getenv("SSH_HOST")
    ssh_port = int(os.getenv("SSH_PORT", "22"))
    ssh_user = os.getenv("SSH_USER")
    ssh_password = os.getenv("SSH_PASSWORD")

    if not ssh_host or not ssh_user:
        await websocket.send_text(
            "Error: SSH_HOST and SSH_USER env vars required on Render"
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
            timeout=15,
        )
        channel = client.invoke_shell(term="xterm-256color", width=120, height=40)
        channel.settimeout(0.0)
        channel.send("\n")  # Trigger initial banner

        print(f"SSH connected to {ssh_host}")

        async def send_output():
            while True:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if not data:
                        break
                    await websocket.send_bytes(data)
                await asyncio.sleep(0.01)

        async def receive_input():
            while True:
                try:
                    message = await websocket.receive_text()
                    channel.send(message.encode("utf-8"))
                except Exception:
                    break

        await asyncio.gather(send_output(), receive_input())

    except Exception as e:
        error_msg = f"SSH Connection Failed: {str(e)}"
        print(error_msg)
        await websocket.send_text(error_msg)
    finally:
        channel.close()
        client.close()
        await websocket.close()
        print("SSH and WebSocket closed")
