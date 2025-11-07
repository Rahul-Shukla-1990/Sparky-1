"""Convenience launcher for the offline maritime demo server.

This wrapper makes it easy to start the WebSocket-enabled MOD showcase on a
local workstation without relying on Poetry or third-party packages.
"""

from __future__ import annotations

import argparse
import threading
import time
import webbrowser

from backend.app.demo_server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the maritime demo server")
    parser.add_argument("--host", default="0.0.0.0", help="Interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the Maritime Operations Display in the default browser.",
    )
    args = parser.parse_args()

    if args.open:
        thread = threading.Thread(target=serve, kwargs={"host": args.host, "port": args.port}, daemon=False)
        thread.start()
        time.sleep(1.5)
        try:
            webbrowser.open(f"http://{args.host if args.host != '0.0.0.0' else '127.0.0.1'}:{args.port}/")
        except Exception:
            pass
        thread.join()
    else:
        serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
