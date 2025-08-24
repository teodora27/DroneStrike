# camera_stream.py
import cv2
import threading
import time

import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
# Disable hardware transforms for Media Foundation backend

class CameraStream:
    """Simple threaded wrapper around cv2.VideoCapture."""

    def __init__(self, stream_url: str):
        """Start grabbing frames from the given URL."""
        self.cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        if not self.cap.isOpened():
            raise Exception("Cannot open stream. Check the URL and your network connection.")
        self.latest_frame = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, daemon=True)
        time.sleep(2)  # Allow some time for the camera to warm up
        self.thread.start()
    
    def update(self):
        """Background thread that continuously reads frames."""
        while self.running:
            time.sleep(0.1)
            if not self.cap.grab():
                # Grab failed, skip this iteration
                print("Failed to grab frame.")
                continue
            ret, frame = self.cap.retrieve()
            if not ret:
                print("Failed to retrieve frame.")
                continue
            with self.lock:
                self.latest_frame = frame

    def read(self):
        """Return the most recent frame (thread-safe)."""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        """Stop the capture thread and release resources."""
        self.running = False
        self.thread.join()
        self.cap.release()
