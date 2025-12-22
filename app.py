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
    print("WebSocket accepted")

    ssh_host = os.getenv("SSH_HOST")
    ssh_port = int(os.getenv("SSH_PORT", 22))
    ssh_user = os.getenv("SSH_USER")
    ssh_password = os.getenv("SSH_PASSWORD")

    if not ssh_host or not ssh_user:
        await websocket.send_text(
            "Error: Missing SSH configuration (check Render env vars)"
        )
        await websocket.close()
        return

    client = None
    channel = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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

        print("SSH connected successfully")

        while True:
            # Check for SSH output
            if channel.recv_ready():
                data = channel.recv(4096)
                if not data:
                    break
                await websocket.send_bytes(data)

            # Check for client input
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.1)
                channel.send(data)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                print("WebSocket disconnected gracefully")
                break

    except paramiko.AuthenticationException:
        await websocket.send_text("Authentication failed - check username/password")
    except paramiko.SSHException as e:
        await websocket.send_text(f"SSH error: {str(e)}")
    except Exception as e:
        await websocket.send_text(f"Connection error: {str(e)}")
    finally:
        if channel is not None:
            channel.close()
        if client is not None:
            client.close()
        try:
            await websocket.close()
        except RuntimeError:
            print("Close already in progress - skipping")
        except Exception:
            pass
        print("Cleanup complete")
