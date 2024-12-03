import io
import logging
import socketserver
import os
from http import server
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

# Lấy đường dẫn tuyệt đối của file hiện tại
script_dir = os.path.dirname(os.path.abspath(__file__))
html_file_path = os.path.join(script_dir, "index.html")
css_file_path = os.path.join(script_dir, "style.css")
js_file_path = os.path.join(script_dir, "script.js")
favicon_file_path = os.path.join(script_dir, "favicon.ico")

# Đọc nội dung của file HTML
with open(html_file_path, "r") as file:
    PAGE = file.read()

# Đọc nội dung của file CSS
with open(css_file_path, "r") as file:
    STYLES = file.read()

# Đọc nội dung của file JS
with open(js_file_path, "r") as file:
    SCRIPT = file.read()

# Đọc nội dung của file favicon.ico
with open(favicon_file_path, "rb") as file:
    FAVICON = file.read()


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(301)
            self.send_header("Location", "/index.html")
            self.end_headers()
        elif self.path == "/index.html":
            content = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/styles.css":
            content = STYLES.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/css")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/script.js":
            content = SCRIPT.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/favicon.ico":
            self.send_response(200)
            self.send_header("Content-Type", "image/x-icon")
            self.send_header("Content-Length", len(FAVICON))
            self.end_headers()
            self.wfile.write(FAVICON)
        elif self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header("Age", 0)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
            )
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b"--FRAME\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except Exception as e:
                logging.warning(
                    "Removed streaming client %s: %s", self.client_address, str(e)
                )
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

try:
    address = ("", 85)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
