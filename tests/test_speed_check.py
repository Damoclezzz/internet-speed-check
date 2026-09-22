import contextlib
import io
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import speed_check


PAYLOAD = b"speed-test-data" * 4096


class DownloadHandler(BaseHTTPRequestHandler):
    request_count = 0
    active_requests = 0
    max_active_requests = 0
    response_code = 200

    def do_GET(self):
        DownloadHandler.request_count += 1
        DownloadHandler.active_requests += 1
        DownloadHandler.max_active_requests = max(
            DownloadHandler.max_active_requests, DownloadHandler.active_requests
        )
        try:
            self.send_response(DownloadHandler.response_code)
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            if DownloadHandler.response_code == 200:
                self.wfile.write(PAYLOAD)
        finally:
            DownloadHandler.active_requests -= 1

    def log_message(self, format, *args):
        pass


class SpeedCheckTests(unittest.TestCase):
    def setUp(self):
        DownloadHandler.request_count = 0
        DownloadHandler.active_requests = 0
        DownloadHandler.max_active_requests = 0
        DownloadHandler.response_code = 200
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/file"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()

    def test_ten_complete_sequential_downloads(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with patch("sys.argv", ["speed_check.py", self.url]):
                result = speed_check.main()

        self.assertEqual(result, 0)
        self.assertEqual(DownloadHandler.request_count, 10)
        self.assertEqual(DownloadHandler.max_active_requests, 1)
        self.assertIn(f"Всего скачано: {len(PAYLOAD) * 10} байт", output.getvalue())
        self.assertIn("Скорость скачивания:", output.getvalue())
        self.assertIn("Мбит/с", output.getvalue())

    def test_http_error_stops_measurement(self):
        DownloadHandler.response_code = 404
        error_output = io.StringIO()
        with contextlib.redirect_stderr(error_output):
            with patch("sys.argv", ["speed_check.py", self.url]):
                result = speed_check.main()

        self.assertEqual(result, 1)
        self.assertEqual(DownloadHandler.request_count, 1)
        self.assertIn("Ошибка при запросе 1/10", error_output.getvalue())

    def test_speed_is_measured_in_megabits(self):
        self.assertEqual(speed_check.calculate_speed_mbps(1_000_000, 2), 4)


if __name__ == "__main__":
    unittest.main()
