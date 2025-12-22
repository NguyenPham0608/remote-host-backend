import asyncio
import websockets
import asyncssh
import os
import sys
import logging

# Configure logging to see events in the Render Dashboard logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SSH_Relay")

# Load Environment Variables
SSH_HOST = os.environ.get("SSH_HOST")
SSH_PORT = int(os.environ.get("SSH_PORT", 22))
SSH_USER = os.environ.get("SSH_USER")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD")
PORT = int(os.environ.get("PORT", 8765))


async def ssh_handler(websocket):
    logger.info("New WebSocket connection established.")

    # 1. Validate Config
    if not all([SSH_HOST, SSH_USER, SSH_PASSWORD]):
        msg = "ERROR: Missing SSH_HOST, SSH_USER, or SSH_PASSWORD in environment variables."
        logger.error(msg)
        await websocket.send(f"\r\n\x1b[31m[CONFIG ERROR] {msg}\x1b[0m\r\n")
        return

    try:
        logger.info(f"Connecting to SSH: {SSH_USER}@{SSH_HOST}:{SSH_PORT}")

        # 2. Establish SSH Connection
        async with asyncssh.connect(
            SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            known_hosts=None,  # Skips host key check for simplicity
        ) as conn:

            logger.info("SSH Authentication Successful.")

            # 3. Create Interactive Shell (xterm)
            async with conn.create_process(
                term_type="xterm", term_size=(80, 24)
            ) as process:

                # Forward Browser Keystrokes -> SSH Input
                async def ws_to_ssh():
                    try:
                        async for message in websocket:
                            process.stdin.write(message)
                    except Exception as e:
                        logger.info(f"WS to SSH closed: {e}")

                # Forward SSH Output -> Browser Display
                async def ssh_to_ws():
                    try:
                        while not process.stdout.at_eof():
                            data = await process.stdout.read(4096)
                            if data:
                                await websocket.send(data)
                            else:
                                break
                    except Exception as e:
                        logger.info(f"SSH to WS closed: {e}")

                # Run both directions concurrently
                await asyncio.gather(ws_to_ssh(), ssh_to_ws())

    except Exception as e:
        err_msg = f"SSH CONNECTION FAILED: {str(e)}"
        logger.error(err_msg)
        if not websocket.closed:
            await websocket.send(f"\r\n\x1b[31m{err_msg}\x1b[0m\r\n")
    finally:
        logger.info("WebSocket connection closing.")


async def main():
    logger.info(f"Server starting on 0.0.0.0:{PORT}")
    # Render requires binding to 0.0.0.0
    async with websockets.serve(ssh_handler, "0.0.0.0", PORT):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    # Windows-specific fix for asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
