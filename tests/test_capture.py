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


PAGES = {
    "/": b'<form method="post" action="/pay"><button id="pay">Pay</button></form>'
         b'<script>fetch("/api/pay", {method: "POST"})</script>',
    "/popup-page": b'<button id="pay" onclick="window.open(\'/popup\')">Pay</button>',
    "/popup": b'<script>fetch("/api/charge", {method: "POST"})</script>',
    "/ws-page": b'<button id="pay" onclick="var s = new WebSocket(\'ws://\' + location.host + \'/ws\');'
                b' s.onopen = function () { s.send(\'PAY\'); }">Pay</button>',
}


class Recorder(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Recorder.seen.append(("GET", self.path, self.headers.get("Upgrade", "")))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGES.get(self.path, b""))

    def do_POST(self):
        Recorder.seen.append(("POST", self.path, ""))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class CaptureSmoke(unittest.TestCase):
    def setUp(self):
        Recorder.seen = []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def capture(self, path, *steps):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "shot.png"
            res = subprocess.run([sys.executable, str(ENGINE / "capture.py"),
                                  f"http://127.0.0.1:{self.server.server_port}{path}", "--out", str(out),
                                  *steps], capture_output=True, text=True)
            if res.returncode == 3 or "Executable doesn't exist" in res.stderr:
                self.skipTest("no browser")
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(out.exists())

    def test_click_on_submit_never_reaches_the_server(self):
        self.capture("/", "--click", "#pay", "--wait", "300")
        self.assertIn(("GET", "/", ""), Recorder.seen)
        self.assertFalse([s for s in Recorder.seen if s[0] == "POST"])

    def test_popup_cannot_send_either(self):
        self.capture("/popup-page", "--click", "#pay", "--wait", "800")
        self.assertIn(("GET", "/popup-page", ""), Recorder.seen)
        self.assertFalse([s for s in Recorder.seen if s[0] == "POST"], Recorder.seen)

    def test_websocket_never_reaches_the_server(self):
        self.capture("/ws-page", "--click", "#pay", "--wait", "800")
        self.assertIn(("GET", "/ws-page", ""), Recorder.seen)
        self.assertFalse([s for s in Recorder.seen if s[2].lower() == "websocket"], Recorder.seen)

    def test_page_that_never_loads_exits_1_with_one_line(self):
        res = subprocess.run([sys.executable, str(ENGINE / "capture.py"), "http://127.0.0.1:9/",
                              "--out", "never.png"], capture_output=True, text=True)
        if res.returncode == 3 or "Executable doesn't exist" in res.stderr:
            self.skipTest("no browser")
        self.assertEqual(res.returncode, 1, res.stderr)
        self.assertNotIn("Traceback", res.stderr)
        self.assertIn("capture failed", res.stderr)


if __name__ == "__main__":
    unittest.main()
