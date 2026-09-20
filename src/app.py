"""
FlowGrid - Web Dashboard Server Launcher
Team Jam Breakers | International Hackathon - Vietnam 2026

Usage:
  python src/app.py
"""

import os
import sys
import webbrowser
import http.server
import socketserver

PORT = 8000
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, format, *args):
        # Clean console logging
        sys.stderr.write(f"[FlowGrid Edge Server] {self.address_string()} - {args[0]}\n")


def main():
    print("=" * 65)
    print("        FLOWGRID WEB DASHBOARD (INTERACTIVE POC)")
    print("=" * 65)
    print(f"[*] Serving dashboard from: {FRONTEND_DIR}")
    print(f"[*] Local URL: http://localhost:{PORT}")
    print("[*] Press Ctrl+C to stop server.\n")

    # Attempt to open browser automatically
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass

    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Server stopped by user.")


if __name__ == "__main__":
    main()
