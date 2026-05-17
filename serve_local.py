#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from urllib.parse import urlparse


class LocalSiteHandler(SimpleHTTPRequestHandler):
    """Serve local static files without aggressive browser caching."""

    annotations_lock = Lock()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/annotations":
            self.send_json(self.read_annotations())
            return

        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path == "/api/annotations/toggle":
            self.handle_toggle_annotation()
            return

        self.send_json({"error": "Not found"}, status=404)

    def read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}

        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8"))

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def annotations_path(self) -> Path:
        return Path("data/annotations.json")

    def read_annotations(self) -> dict:
        path = self.annotations_path()
        if not path.exists():
            return {}

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(data, dict):
            return {}
        return data

    def write_annotations(self, annotations: dict) -> None:
        path = self.annotations_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as tmp:
            json.dump(annotations, tmp, ensure_ascii=False, indent=2, sort_keys=True)
            tmp.write("\n")
            tmp_path = Path(tmp.name)

        tmp_path.replace(path)

    def handle_toggle_annotation(self) -> None:
        try:
            body = self.read_json_body()
            paper_id = str(body.get("paper_id", "")).strip()
            annotation_type = str(body.get("type", "")).strip()
            name = str(body.get("name", "user")).strip() or "user"
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json({"error": "Invalid JSON body"}, status=400)
            return

        if not paper_id:
            self.send_json({"error": "paper_id is required"}, status=400)
            return
        if annotation_type not in {"read", "favorite"}:
            self.send_json({"error": "type must be read or favorite"}, status=400)
            return

        with self.annotations_lock:
            annotations = self.read_annotations()
            paper_annotations = annotations.setdefault(paper_id, {})
            names = paper_annotations.setdefault(annotation_type, [])

            if not isinstance(names, list):
                names = []

            if name in names:
                names = [existing for existing in names if existing != name]
                marked = False
            else:
                names.append(name)
                names = sorted(set(names), key=str.casefold)
                marked = True

            paper_annotations[annotation_type] = names
            paper_annotations.setdefault("read", [])
            paper_annotations.setdefault("favorite", [])
            annotations[paper_id] = paper_annotations
            self.write_annotations(annotations)

        self.send_json(
            {
                "paper_id": paper_id,
                "type": annotation_type,
                "name": name,
                "marked": marked,
                "annotations": annotations,
            }
        )


def discover_lan_ips() -> list[str]:
    ips: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ips.add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            if family == socket.AF_INET:
                ip = sockaddr[0]
                if not ip.startswith("127."):
                    ips.add(ip)
    except socket.gaierror:
        pass

    return sorted(ips)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the local arXiv site on your LAN.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to. Default: 0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to. Default: 8000")
    parser.add_argument(
        "--directory",
        default=".",
        help="Directory to serve. Default: current project root",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    if not directory.exists():
        raise SystemExit(f"Directory does not exist: {directory}")

    os.chdir(directory)
    server = ThreadingHTTPServer((args.host, args.port), LocalSiteHandler)

    print(f"Serving {directory}")
    print(f"Local URL: http://127.0.0.1:{args.port}")
    for ip in discover_lan_ips():
        print(f"LAN URL:   http://{ip}:{args.port}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
