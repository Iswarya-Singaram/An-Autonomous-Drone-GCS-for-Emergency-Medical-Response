# File: stream.py (USB Camera Version)
# Location: Save this in your project folder on the Raspberry Pi
# Description: A standalone script that captures video from a standard USB camera
#              using OpenCV and streams it as an MJPEG feed.

import cv2
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import time

# --- CONFIGURATION ---
VIDEO_RESOLUTION = (640, 480) # Resolution for the USB camera
VIDEO_FRAMERATE = 30          # Framerate to request from the camera
STREAMING_PORT = 8001         # The port the video stream will be available on
JPEG_QUALITY = 80             # JPEG compression quality (0-100)

# --- SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Global variable to hold the latest frame from the camera
latest_frame = None

class CameraStreamHandler(BaseHTTPRequestHandler):
    """A simple HTTP request handler for the MJPEG stream."""
    def do_GET(self):
        global latest_frame
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            while True:
                try:
                    if latest_frame is not None:
                        ret, jpg = cv2.imencode('.jpg', latest_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                        if not ret:
                            continue
                        self.wfile.write(b'--jpgboundary\r\n')
                        self.send_header('Content-type', 'image/jpeg')
                        self.send_header('Content-length', str(len(jpg)))
                        self.end_headers()
                        self.wfile.write(jpg)
                        self.wfile.write(b'\r\n')
                    time.sleep(1 / VIDEO_FRAMERATE)
                except (BrokenPipeError, ConnectionResetError):
                    # Client disconnected
                    break
        else:
            self.send_error(404)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def capture_frames():
    """Continuously capture frames from the USB camera."""
    global latest_frame
    # The '0' argument usually refers to the first USB camera found (/dev/video0)
    # If you have multiple cameras, you might need to change this to 1, 2, etc.
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_RESOLUTION[1])
    cap.set(cv2.CAP_PROP_FPS, VIDEO_FRAMERATE)
    
    if not cap.isOpened():
        logging.error("Cannot open USB camera. Is it connected?")
        return

    logging.info("USB camera opened successfully.")
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.warning("Failed to grab frame from camera.")
            time.sleep(1)
            continue
        latest_frame = frame

def main():
    """Starts the camera capture and the streaming server."""
    try:
        # Start capturing frames in a background thread
        import threading
        capture_thread = threading.Thread(target=capture_frames)
        capture_thread.daemon = True
        capture_thread.start()

        # Start the HTTP server
        server_address = ('', STREAMING_PORT)
        httpd = ThreadedHTTPServer(server_address, CameraStreamHandler)
        logging.info(f"MJPEG server started on port {STREAMING_PORT}")
        httpd.serve_forever()

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
