#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class LocalSiteHandler(SimpleHTTPRequestHandler):
    """Serve local static files without aggressive browser caching."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


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
