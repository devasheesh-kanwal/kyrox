"""Local static server for the ORCA frontend.

Same as `python -m http.server`, but:
  - tells the browser to revalidate every file, so an edited page is never
    replaced by a stale cached copy;
  - answers /env.js with an empty config when the optional file is absent
    (it is git-ignored), so a fresh checkout has no 404 in the console.

Usage: python serve.py [port]   (default 5500)
"""
import http.server
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EMPTY_ENV = b"// No env.js found: using defaults. Copy env.example.js to env.js to configure.\nwindow.__ENV__ = window.__ENV__ || {};\n"


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/env.js" and not (ROOT / "env.js").exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(EMPTY_ENV)))
            self.end_headers()
            self.wfile.write(EMPTY_ENV)
            return
        super().do_GET()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    handler = lambda *args, **kwargs: NoCacheHandler(*args, directory=str(ROOT), **kwargs)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", port), handler) as httpd:
        print(f"Serving ORCA frontend at http://localhost:{port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
