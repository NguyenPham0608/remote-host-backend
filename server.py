import asyncio
import websockets
import asyncssh
import os
import sys

# Configuration: Ideally set these as Environment Variables for security
# For local testing, you can replace os.environ.get with a hardcoded string
SSH_HOST = os.environ.get("SSH_HOST", "your.remote.host")
SSH_PORT = int(os.environ.get("SSH_PORT", 22))
SSH_USER = os.environ.get("SSH_USER", "username")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD", "password")
PORT = int(os.environ.get("PORT", 8765))


async def ssh_handler(websocket):
    print(f"Client connected from {websocket.remote_address}")

    try:
        # Connect to the remote SSH server
        async with asyncssh.connect(
            SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            known_hosts=None,  # Note: In production, verify host keys!
        ) as conn:

            # Create an interactive shell session
            async with conn.create_process(
                term_type="xterm", term_size=(80, 24)
            ) as process:

                # Forward WebSocket messages to SSH stdin
                async def ws_to_ssh():
                    try:
                        async for message in websocket:
                            process.stdin.write(message)
                    except Exception:
                        pass

                # Forward SSH stdout to WebSocket
                async def ssh_to_ws():
                    try:
                        while not process.stdout.at_eof():
                            data = await process.stdout.read(4096)
                            if data:
                                await websocket.send(data)
                            else:
                                break
                    except Exception:
                        pass

                # Run both directions concurrently
                await asyncio.gather(ws_to_ssh(), ssh_to_ws())

    except Exception as e:
        await websocket.send(f"\r\n[Server Error]: {str(e)}\r\n")
    finally:
        print("Connection closed.")


async def main():
    print(f"WebSocket server starting on port {PORT}...")
    async with websockets.serve(ssh_handler, "0.0.0.0", PORT):
        await asyncio.Future()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
