"""Mock Uptime Kuma Push API server for testing."""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from uptime_kuma_satellite.models import MonitorResult, MonitorStatus


class MockKumaHandler(BaseHTTPRequestHandler):
    """Mock handler for Uptime Kuma Push API."""

    received_reports: list[dict] = []

    def do_GET(self) -> None:
        # Parse query params
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        status = params.get("status", [""])[0]
        msg = params.get("msg", [""])[0]
        ping = params.get("ping", [""])[0]

        report = {
            "path": parsed.path,
            "status": status,
            "msg": msg,
            "ping": ping,
            "params": params,
        }
        MockKumaHandler.received_reports.append(report)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format: str, *args: object) -> None:
        # Suppress log output
        pass


def start_mock_server(port: int = 8765) -> HTTPServer:
    """Start the mock server on the given port."""
    MockKumaHandler.received_reports = []
    server = HTTPServer(("127.0.0.1", port), MockKumaHandler)
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Mock Uptime Kuma server starting on port {port}...")
    server = start_mock_server(port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
