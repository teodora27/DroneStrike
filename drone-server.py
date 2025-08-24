"""Minimal Flask server to stream frames from a DJI Tello."""

from flask import Flask, Response
import cv2
from djitellopy import Tello

app = Flask(__name__)

# Open the default camera (0), or replace with your IP camera URL
# camera = cv2.VideoCapture(0)  # or cv2.VideoCapture('http://<ip>:<port>/video')

drone = Tello()
drone.connect()
drone.streamon()
frame_reader = drone.get_frame_read()
print("Drone connected:", drone.get_battery(), "% battery")

#frame_reader.stop()
#drone.streamoff()
#drone.end()

def generate_frames():
    """Generator yielding JPEG frames from the drone."""
    while True:
        # Uncomment the following line to stream from a regular webcam instead
        # success, frame = camera.read()
        success, frame = True, frame_reader.frame
        if not success:
            break
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        # Yield frame in HTTP multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Stream the MJPEG feed to the browser."""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/do', methods=['POST'])
def do_something():
    """Placeholder endpoint used for quick testing."""
    result = "Hello, World!"
    return f"Function called! Result: {result}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
