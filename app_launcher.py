"""Desktop launcher for RepoTranslate.

Starts the FastAPI server, then opens a native Windows window.
Tries pywebview first, falls back to browser if it fails.
"""

import os
import sys
import time
import threading
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 9000
URL = f"http://{HOST}:{PORT}"


def start_server():
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")


def try_webview():
    """Try to open a native window. Returns True if successful."""
    try:
        import webview
        webview.create_window(
            title="RepoTranslate - GitHub",
            url=URL,
            width=1100,
            height=800,
            min_size=(800, 600),
        )
        webview.start()
        return True
    except Exception as e:
        logger.warning(f"Native window failed: {e}")
        return False


def try_edge_app():
    """Use Microsoft Edge in app mode (no address bar, looks native)."""
    try:
        subprocess.run([
            "start", "msedge",
            f"--app={URL}",
            "--window-size=1100,800",
        ], shell=True, check=True)
        return True
    except Exception as e:
        logger.warning(f"Edge app mode failed: {e}")
        return False


def main():
    print("=" * 50)
    print("  RepoTranslate v0.1.0")
    print("=" * 50)

    # Start server
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(2)

    # Try native window, then Edge app mode, then browser
    if try_webview():
        return
    if try_edge_app():
        return

    # Last resort: open browser
    import webbrowser
    print(f"Opening browser: {URL}")
    webbrowser.open(URL)

    try:
        while t.is_alive():
            t.join(1)
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
