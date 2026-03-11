#!/usr/bin/env python3
"""Local dev server with lightweight live-reload for static files.

Run from project root:
    python scripts/dev_server.py

Then open:
    http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WATCH_EXTENSIONS = {".html", ".css", ".js", ".json", ".csv"}
POLL_INTERVAL_SECONDS = 1.0


LIVE_RELOAD_SNIPPET = """
<script>
(function () {
  var current = null;

  function check() {
    fetch('/__reload_version', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (current === null) {
          current = data.version;
          return;
        }
        if (data.version !== current) {
          location.reload();
        }
      })
      .catch(function () {
        // Keep polling even if the endpoint is briefly unavailable.
      });
  }

  check();
  setInterval(check, 1000);
})();
</script>
""".strip()


class VersionTracker:
    """Tracks the newest file modification timestamp in the workspace."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = threading.Lock()
        self._version = "0"

    def get(self) -> str:
        with self._lock:
            return self._version

    def set(self, value: str) -> None:
        with self._lock:
            self._version = value


def compute_workspace_version(root: Path) -> str:
    latest_mtime = 0.0
    latest_file = ""

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip VCS/cache folders for speed.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in {".git", "__pycache__", ".venv", "venv"}
        ]

        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() not in WATCH_EXTENSIONS:
                continue

            try:
                stat = path.stat()
            except OSError:
                continue

            if stat.st_mtime > latest_mtime:
                latest_mtime = stat.st_mtime
                latest_file = str(path.relative_to(root)).replace("\\", "/")

    # Include file name so multiple files saved in same timestamp still update.
    return f"{latest_mtime:.6f}:{latest_file}"


def start_watcher(tracker: VersionTracker, interval: float) -> None:
    while True:
        version = compute_workspace_version(tracker.root)
        if version != tracker.get():
            tracker.set(version)
            print(f"[reload] {version}")
        time.sleep(interval)


class LiveReloadHandler(SimpleHTTPRequestHandler):
    tracker: VersionTracker

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/__reload_version":
            payload = json.dumps(
                {"version": self.tracker.get()}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/__save_csv":
            content_length = int(
                self.headers.get("Content-Length", 0)
            )
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                file_path = data.get("path", "")
                csv_content = data.get("content", "")

                # Prevent path traversal attacks
                if ".." in file_path or file_path.startswith("/"):
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {"error": "Invalid path"}
                        ).encode("utf-8")
                    )
                    return

                # Resolve path relative to project root
                target_path = Path(self.directory) / file_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(csv_content, encoding="utf-8")

                response = json.dumps(
                    {"success": True}
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            except (json.JSONDecodeError, KeyError, OSError) as e:
                error_msg = json.dumps(
                    {"error": str(e)}
                ).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error_msg)))
                self.end_headers()
                self.wfile.write(error_msg)
            return

        self.send_response(404)
        self.end_headers()

    def send_head(self):
        parsed = urlparse(self.path)

        if parsed.path.endswith(".html") or parsed.path in {"", "/"}:
            local = parsed.path.lstrip("/") or "index.html"
            target = Path(self.directory) / local
            if target.exists() and target.is_file():
                try:
                    html = target.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    # Fallback to normal behavior for non-UTF8 files.
                    return super().send_head()

                if "__reload_version" not in html:
                    lower = html.lower()
                    if "</body>" in lower:
                        idx = lower.rfind("</body>")
                        html = (
                            html[:idx]
                            + "\n"
                            + LIVE_RELOAD_SNIPPET
                            + "\n"
                            + html[idx:]
                        )
                    else:
                        html = html + "\n" + LIVE_RELOAD_SNIPPET + "\n"

                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return None

        return super().send_head()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static dev server with live reload"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=POLL_INTERVAL_SECONDS,
        help=(
            "File watch interval in seconds "
            f"(default: {POLL_INTERVAL_SECONDS})"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tracker = VersionTracker(PROJECT_ROOT)
    tracker.set(compute_workspace_version(PROJECT_ROOT))

    watcher = threading.Thread(
        target=start_watcher,
        args=(tracker, args.interval),
        daemon=True,
    )
    watcher.start()

    handler_cls = partial(LiveReloadHandler, directory=str(PROJECT_ROOT))
    handler_cls.tracker = tracker

    server = ThreadingHTTPServer((args.host, args.port), handler_cls)

    print(f"Serving {PROJECT_ROOT}")
    print(f"URL: http://{args.host}:{args.port}")
    print(
        "Live reload is enabled. Save a file and the browser refreshes "
        "automatically."
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
