"""Desktop launcher for RepoTranslate.

Starts the FastAPI server in a background thread, then opens
the default web browser. Used by PyInstaller to build the EXE.

Build command:
    pyinstaller --onefile --add-data "app;app" --add-data "app/web/templates;app/web/templates" --add-data "app/web/static;app/web/static" --hidden-import uvicorn.logging --hidden-import uvicorn.loops --hidden-import uvicorn.protocols app_launcher.py
"""

import os
import sys
import time
import webbrowser
import threading
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 9000
URL = f"http://{HOST}:{PORT}"


def _get_base_dir():
    """Get the directory containing the app, works in both dev and PyInstaller."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def start_server():
    """Start uvicorn in a background thread."""
    import uvicorn

    config = uvicorn.Config(
        "app.main:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    print("=" * 50)
    print("  RepoTranslate v0.1.0")
    print(f"  启动后浏览器会自动打开 {URL}")
    print("  关闭此窗口即可退出")
    print("=" * 50)

    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait for server to be ready
    time.sleep(2)

    # Open browser
    print(f"\n正在打开浏览器...")
    webbrowser.open(URL)

    print(f"服务运行中: {URL}")
    print("按 Ctrl+C 或关闭此窗口退出\n")

    try:
        while server_thread.is_alive():
            server_thread.join(1)
    except KeyboardInterrupt:
        print("\n正在退出...")


if __name__ == "__main__":
    main()
