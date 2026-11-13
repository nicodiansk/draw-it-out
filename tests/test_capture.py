"""capture.py: the safety rules without a browser, then one real capture when Playwright is there."""
import http.server
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from helpers import ENGINE
import capture as C

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class Safety(unittest.TestCase):
    def test_only_localhost_pages(self):
        self.assertTrue(C.is_local("http://localhost:3000/checkout"))
        self.assertTrue(C.is_local("http://127.0.0.1:8000"))
        self.assertTrue(C.is_local("http://[::1]:5173/"))
        self.assertFalse(C.is_local("https://example.com"))
        self.assertFalse(C.is_local("http://localhost.evil.com"))
        self.assertFalse(C.is_local("file:///etc/passwd"))

    def test_only_read_requests_to_localhost(self):
        self.assertTrue(C.allow_request("GET", "http://localhost:3000/app.js"))
        self.assertFalse(C.allow_request("POST", "http://localhost:3000/api/pay"))
        self.assertFalse(C.allow_request("PUT", "http://localhost:3000/api/cart"))
        self.assertFalse(C.allow_request("GET", "https://fonts.example.com/a.woff2"))

    def test_steps_keep_their_order(self):
        args = C.parse(["http://localhost:3000", "--out", "a.png", "--click", "text=Pay", "--wait", "500", "--click", "#ok"])
        self.assertEqual(args.steps, [("click", "text=Pay"), ("wait", "500"), ("click", "#ok")])

    def test_remote_url_refused_before_any_browser(self):
        res = subprocess.run([sys.executable, str(ENGINE / "capture.py"), "https://example.com", "--out", "x.png"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertIn("only http(s)://localhost", res.stderr)

    def test_wait_capped(self):
        with self.assertRaises(SystemExit):
            C.parse(["http://localhost:3000", "--out", "a.png", "--wait", "60000"])


class Recorder(http.server.BaseHTTPRequestHandler):
    seen = []
    PAGE = (b'<form method="post" action="/pay"><button id="pay">Pay</button></form>'
            b'<script>fetch("/api/pay", {method: "POST"})</script>')

    def do_GET(self):
        Recorder.seen.append(("GET", self.path))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.PAGE)

    def do_POST(self):
        Recorder.seen.append(("POST", self.path))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class CaptureSmoke(unittest.TestCase):
    def test_click_on_submit_never_reaches_the_server(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "shot.png"
            res = subprocess.run([sys.executable, str(ENGINE / "capture.py"),
                                  f"http://127.0.0.1:{server.server_port}/", "--out", str(out),
                                  "--click", "#pay", "--wait", "300"], capture_output=True, text=True)
            server.shutdown()
            if res.returncode == 3 or "Executable doesn't exist" in res.stderr:
                self.skipTest("no browser")
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(out.exists())
        self.assertIn(("GET", "/"), Recorder.seen)
        self.assertFalse([s for s in Recorder.seen if s[0] == "POST"])


if __name__ == "__main__":
    unittest.main()
