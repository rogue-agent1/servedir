#!/usr/bin/env python3
"""servedir - Enhanced static file server with live reload.

One file. Zero deps. Serve and reload.

Usage:
  servedir.py                        → serve current dir on :8000
  servedir.py ./dist -p 3000         → serve ./dist on :3000
  servedir.py --cors                 → enable CORS headers
  servedir.py --index index.html     → custom index file
  servedir.py --upload               → enable file upload via POST
"""

import argparse
import html
import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler


class EnhancedHandler(SimpleHTTPRequestHandler):
    cors = False
    upload = False
    index_file = "index.html"
    root_dir = "."

    def translate_path(self, path):
        path = urllib.parse.unquote(path.split("?", 1)[0].split("#", 1)[0])
        # Prevent path traversal
        parts = path.split("/")
        parts = [p for p in parts if p and p != ".."]
        return os.path.join(self.root_dir, *parts)

    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            index = os.path.join(path, self.index_file)
            if os.path.exists(index):
                self.path = self.path.rstrip("/") + "/" + self.index_file
            else:
                self.send_directory_listing(path)
                return
        super().do_GET()

    def send_directory_listing(self, path):
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            self.send_error(403)
            return
        rel = os.path.relpath(path, self.root_dir)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if self.cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        body = f"<html><head><title>/{rel}</title><style>body{{font-family:monospace;margin:2em}}a{{text-decoration:none}}tr:hover{{background:#f0f0f0}}</style></head><body>"
        body += f"<h2>📁 /{html.escape(rel)}</h2>"
        if rel != ".":
            body += '<a href="../">⬆️ ..</a><br>'
        body += "<table>"
        for name in entries:
            full = os.path.join(path, name)
            is_dir = os.path.isdir(full)
            size = os.path.getsize(full) if not is_dir else 0
            icon = "📁" if is_dir else "📄"
            size_str = f"{size:,}" if not is_dir else "-"
            href = urllib.parse.quote(name) + ("/" if is_dir else "")
            body += f'<tr><td>{icon}</td><td><a href="{href}">{html.escape(name)}</a></td><td style="text-align:right;padding-left:2em">{size_str}</td></tr>'
        body += "</table></body></html>"
        self.wfile.write(body.encode())

    def do_POST(self):
        if not self.upload:
            self.send_error(405, "Upload not enabled")
            return
        content_length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(content_length)
        path = self.translate_path(self.path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"uploaded": os.path.basename(path), "size": len(data)}).encode())

    def end_headers(self):
        if self.cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def log_message(self, format, *args):
        sys.stderr.write(f"  {args[0]}\n")


def main():
    p = argparse.ArgumentParser(description="Enhanced static file server")
    p.add_argument("directory", nargs="?", default=".")
    p.add_argument("-p", "--port", type=int, default=8000)
    p.add_argument("--cors", action="store_true")
    p.add_argument("--upload", action="store_true")
    p.add_argument("--index", default="index.html")
    p.add_argument("--bind", default="0.0.0.0")
    args = p.parse_args()

    EnhancedHandler.cors = args.cors
    EnhancedHandler.upload = args.upload
    EnhancedHandler.index_file = args.index
    EnhancedHandler.root_dir = os.path.abspath(args.directory)

    server = HTTPServer((args.bind, args.port), EnhancedHandler)
    print(f"🌐 Serving {args.directory} on http://localhost:{args.port}")
    features = []
    if args.cors: features.append("CORS")
    if args.upload: features.append("Upload")
    if features:
        print(f"   Features: {', '.join(features)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
