"""
DJI Tello continuous keyboard control + live YOLO detection (modular)

Controls
--------
  W/S  : pitch  ±50 cm/s   (forward / back)
  A/D  : roll   ±50 cm/s   (left / right)
  I/K  : throttle ±50 cm/s (up / down)
  J/L  : yaw    ±50 deg/s
  0    : toggle autopilot (search / chase)
  Space / Esc : land and quit

Autopilot logic (v4)
--------------------
* **Search mode** – no recent person: slow clockwise spin.
* **Chase mode** – person detected within last ≤ 10 frames:
    * Horizontal: turn **left** if box‑centre x < 0.5 else **right**.
    * Vertical:   if top‑y < 0.5 ⇒ **descend** (go down)
                  if top‑y > 0.5 ⇒ **ascend**  (go up)
    * A red circle marks the guidance point *(xmid, ytop)*.
* Keyboard inputs still mix in at any time.

Overlays (each frame)
---------------------
  BAT   – battery %
  ALT   – height (cm)
  FPS   – video frame‑rate
  AUTO  – OFF / SEARCH / CHASE(n)
  YOLO  – bounding boxes + labels (+ coords & red dot for person)
  HELP  – key cheatsheet

Dependencies
------------
    pip install djitellopy ultralytics opencv-python keyboard torch
"""

from collections import deque
import time
import cv2
import keyboard
import torch
import threading
import numpy as np
from ultralytics import YOLO
from djitellopy import Tello
from flask import Flask, Response

# Global drone instance and takeoff flag shared between threads
drone = None
takeoff_event = threading.Event()
from autopilot import Autopilot, OffState, SearchState, TrackState

# --------------------------------------------------------------------------- #
# Flask web server setup. This exposes a simple endpoint for streaming the
# drone's camera feed to a browser.  Frames are supplied by the main drone loop
# using a shared memory buffer protected by a lock.
# --------------------------------------------------------------------------- #

app = Flask(__name__)

stream_frame_lock = threading.Lock()
stream_shared_frame = {"frame": None}

def generate_frames():
    """Yield encoded JPEG frames for the web stream."""
    while True:
        # Obtain the latest frame in a thread-safe manner
        with stream_frame_lock:
            frame = stream_shared_frame["frame"]

        if frame is None:
            # If no frame is available yet, send a blank image so the client
            # keeps receiving data and the connection stays open.
            black = (255 * np.zeros((480, 640, 3), dtype=np.uint8))
            ret, buffer = cv2.imencode('.jpg', black)
            time.sleep(0.2)
        else:
            # Encode the frame read from the drone
            ret, buffer = cv2.imencode('.jpg', frame)

        frame_bytes = buffer.tobytes()
        # Multipart response required by HTML5 video streaming via MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """HTTP endpoint returning the MJPEG video stream."""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/do', methods=['POST'])
def do_something():
    """Trigger drone takeoff via HTTP."""
    takeoff_event.set()
    return "Takeoff command sent"

# --------------------------------------------------------------------------- #
# 1.  Model‑loader                                                            #
# --------------------------------------------------------------------------- #

def load_detector(model_path: str = "yolov8n.pt", imgsz: int = 416, prefer_gpu: bool = True) -> YOLO:
    """Load a YOLOv8 model and move it to the appropriate device."""
    # Load the model weights from disk
    model = YOLO(model_path)

    # Select GPU if available and requested, otherwise fall back to CPU
    model.to("cuda" if prefer_gpu and torch.cuda.is_available() else "cpu")
    # Fuse model layers for slightly faster inference
    model.fuse()
    # Set the default inference resolution
    model.imgsz = imgsz
    return model

# --------------------------------------------------------------------------- #
# 2.  Main flight loop                                                        #
# --------------------------------------------------------------------------- #


def run_drone(
              detect_hz: int = 10,
              loop_hz: int = 100,
              speed_xy: int = 100,
              speed_z: int = 100,
              speed_yaw: int = 100) -> None:
    """Main control loop for the drone.

    This function spawns two background threads: one for reading frames from the
    drone and another for running the YOLO detector.  The main thread handles
    keyboard input and issues movement commands based on autopilot mode.
    """

    FONT, FPS_SMOOTH = cv2.FONT_HERSHEY_SIMPLEX, 30

    # ---------------- Overlay helpers -------------------------------------
    def overlay_telemetry(frame, batt, alt, fps, mode, counter):
        """Draw basic telemetry and helper text on the frame."""
        header = {0: "AUTO OFF", 1: "SEARCHING…", 2: f"KILL MODE ({counter})", 3: "TRACK MODE"}[mode]
        lines = [header,
                 f"BAT  {batt:>3}%",
                 f"ALT  {alt:>3} cm",
                 f"FPS  {fps:>4.1f}",
                 "HELP W/S A/D I/K J/L 0=AUTO SPACE=LAND"]
        for i, txt in enumerate(lines):
            cv2.putText(frame, txt, (10, 30 + i * 25), FONT, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    def overlay_dets(frame, dets, chase_pt=None):
        """Render detection results and optional chase point."""
        h, w = frame.shape[:2]
        largest = detection_result.get("person_box")
        for x1, y1, x2, y2, cls, conf in dets:
            if cls == "person":
                is_largest = largest == (x1, y1, x2, y2)
                color, thick = ((0, 255, 0), 4) if is_largest else ((0, 0, 255), 4)
            else:
                color, thick = (0, 255, 255), 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thick)
            lbl = f"{cls} {conf:.2f}"
            cv2.putText(frame, lbl, (x1, max(y1 - 6, 15)), FONT, 0.55, color, 1, cv2.LINE_AA)
            if cls == "person":
                x1n, y1n = x1 / w, y1 / h
                x2n, y2n = x2 / w, y2 / h
                txt_scale = 0.45
                cv2.putText(frame, f"TL({x1n:.3f},{y1n:.3f})", (x1, y1 - 20 if y1 - 20 > 15 else y1 + 15), FONT, txt_scale, color, 1, cv2.LINE_AA)
                cv2.putText(frame, f"TR({x2n:.3f},{y1n:.3f})", (x2 - 140, y1 - 20 if y1 - 20 > 15 else y1 + 15), FONT, txt_scale, color, 1, cv2.LINE_AA)
                cv2.putText(frame, f"BR({x2n:.3f},{y2n:.3f})", (x2 - 140, y2 + 18), FONT, txt_scale, color, 1, cv2.LINE_AA)
                cv2.putText(frame, f"BL({x1n:.3f},{y2n:.3f})", (x1, y2 + 18), FONT, txt_scale, color, 1, cv2.LINE_AA)
        # Draw the red guidance point that autopilot aims for
        if chase_pt is not None:
            cx, cy = chase_pt
            cv2.circle(frame, (int(cx), int(cy)), 8, (0, 0, 255), -1)

    # ---------------- Drone setup -----------------------------------------
    # Connect to the drone and start the video stream
    global drone, takeoff_event
    drone = Tello()
    drone.connect()
    drone.streamon()
    frame_reader = drone.get_frame_read()
    print("Drone connected:", drone.get_battery(), "% battery")

    # ---------------- Loop state ------------------------------------------
    fps_times = deque(maxlen=FPS_SMOOTH)
    last_detect = 0.0
    detections = []
    detection_lock = threading.Lock()
    detection_result = {"boxes": [], "person_box": None}
    frame_lock = threading.Lock()
    shared_frame = {"frame": None}

    autopilot = Autopilot(speed_xy, speed_z, speed_yaw)
    key0_prev = False

    mode=0
    # --- Detection thread function ---
    def detection_thread_func():
        """Run YOLO detection asynchronously from the camera thread."""
        print("Loading detector in detection thread...")
        detector = load_detector("yolov8n.pt")
        print("Detector loaded.")
        while not stop_event.is_set():
            with frame_lock:
                frame = shared_frame["frame"]
            if frame is not None:
                # print(frame.shape, "frame received in detection thread")
                results = detector(frame, verbose=False)[0]
                dets = []
                person_box = None
                largest_area = 0
                for box, cls_id, conf in zip(results.boxes.xyxy.int().tolist(),
                                             results.boxes.cls.int().tolist(),
                                             results.boxes.conf.tolist()):
                    x1, y1, x2, y2 = box
                    cls_name = detector.names[cls_id]
                    dets.append((x1, y1, x2, y2, cls_name, conf))
                    if cls_name == "person":
                        area = (x2 - x1) * (y2 - y1)
                        if area > largest_area:
                            largest_area = area
                            person_box = (x1, y1, x2, y2)
                with detection_lock:
                    detection_result["boxes"] = dets
                    detection_result["person_box"] = person_box
            time.sleep(1 / detect_hz)

    # --- Camera thread function ---
    def camera_thread_func():
        """Grab frames from the drone and draw overlays."""
        nonlocal detections
        while not stop_event.is_set():
            frame = frame_reader.frame
            with frame_lock:
                shared_frame["frame"] = frame.copy() if frame is not None else None

            # --- Overlay detection results and telemetry ---
            if frame is not None:
                with detection_lock:
                    dets = list(detection_result["boxes"])
                # Use shared variables from outer scope
                chase_pt_px = (
                    autopilot.last_xmid * frame.shape[1],
                    autopilot.last_ytop * frame.shape[0]
                ) if autopilot.chase_counter > 0 else None
                overlay_dets(frame, dets, chase_pt_px)
                fps_times.append(time.perf_counter())
                fps = (
                    (len(fps_times) - 1) / (fps_times[-1] - fps_times[0])
                    if len(fps_times) > 1 else 0.0
                )
                overlay_telemetry(frame, drone.get_battery(), drone.get_height(), fps, autopilot.mode, autopilot.chase_counter)

                with stream_frame_lock:
                    stream_shared_frame["frame"] = frame.copy()
            time.sleep(1/loop_hz)  # throttle the loop to avoid overloading the drone

    stop_event = threading.Event()
    det_thread = threading.Thread(target=detection_thread_func,daemon=False)
    cam_thread = threading.Thread(target=camera_thread_func,daemon=False)
    det_thread.start()
    cam_thread.start()

            # ---- 1. Wait for first frame before entering main loop ----------
    frame = None
    while frame is None:
        with frame_lock:
            frame = shared_frame["frame"].copy() if shared_frame["frame"] is not None else None
        if frame is None:
            time.sleep(1/loop_hz)  # wait for a frame to be available
    fh, fw = frame.shape[:2]
    #????
    fh = 720
    fw = 960

    # ---------------- Main loop -------------------------------------------
    print("Press '5' to take off, '0' to toggle autopilot, 'Space' or 'Esc' to land and quit.")


    flying = False

    x1, y1, x2 = 0.5, 0.5, 0.5  # initial box centre (norm)
    yaw_auto, ud_auto = 0, 0  # autopilot commands
    fb_auto = 0  # forward/backward autopilot command

    try:

        while True:
            t0 = time.perf_counter()

            # ---- 0. Autopilot mode switching with keys ----------------------
            #    1 -> manual control
            #    0 -> search mode
            #    2 -> tracking mode
            if keyboard.is_pressed('1'):
                autopilot.set_state(OffState())
                print("AUTOPILOT OFF")
            elif keyboard.is_pressed('0'):
                autopilot.set_state(SearchState())
                print("AUTOPILOT SEARCH")
            elif keyboard.is_pressed('2'):
                autopilot.set_state(TrackState())
                print("AUTOPILOT TRACK")

            # ---- 2. Get detection results from detection thread ------------
            # Pull the most recent person bounding box from the shared result
            with detection_lock:
                person_box = detection_result["person_box"]

            autopilot.update_detection(person_box, fw, fh)
            if person_box is not None:
                x1, y1, x2, y2 = person_box

            # ---- 4. Autopilot commands -----------------------------------
            yaw_auto, ud_auto, fb_auto, _ = autopilot.update()

            lr = (speed_xy if keyboard.is_pressed('d') else -speed_xy if keyboard.is_pressed('a') else 0)
            fb = (speed_xy if (keyboard.is_pressed('w')) else -5*speed_xy if keyboard.is_pressed('s') else 0)
            ud_manual = (speed_z if keyboard.is_pressed('i') else -speed_z if keyboard.is_pressed('k') else 0)
            yaw_manual = (speed_yaw if keyboard.is_pressed('l') else -speed_yaw if keyboard.is_pressed('j') else 0)

            #ud_cmd = max(-100, min(100, ud_manual + ud_auto))
            #yaw_cmd = max(-100, min(100, yaw_manual + yaw_auto))

            # Clamp values to [-100, 100]
            def clamp(val, min_val=-100, max_val=100):
                return max(min_val, min(max_val, val))

            # Example usage
            lr = clamp(lr)
            fb = clamp(fb+ fb_auto)
            ud = clamp(ud_manual+ ud_auto)
            yaw = clamp(yaw_manual+ yaw_auto)

            if flying:
                # ---- 5. Manual inputs ---------------------------------------
                print(fw, fh)
                print(x1, y1, x2, "last_xmid:", autopilot.last_xmid, "last_ytop:", autopilot.last_ytop)
                print("Autopilot mode:", autopilot.name)
                print("fb_auto:", fb_auto, "ud_auto:", ud_auto, "yaw_auto:", yaw_auto)
                print("lr:", lr, "fb:", fb, "ud:", ud, "yaw:", yaw)
                drone.send_rc_control(int(lr), int(fb), int(ud), int(yaw))
                time.sleep(1/loop_hz)  # throttle the loop to avoid overloading the drone
            else:
                if keyboard.is_pressed('5') or takeoff_event.is_set():
                    drone.takeoff()
                    flying = True
                    takeoff_event.clear()
                    print("Drone is now flying.")
                else:
                    print(fw, fh)
                    print(x1, y1, x2, "last_xmid:", autopilot.last_xmid, "last_ytop:", autopilot.last_ytop)
                    print("Autopilot mode:", autopilot.name)
                    print("fb_auto:", fb_auto, "ud_auto:", ud_auto, "yaw_auto:", yaw_auto)
                    print("lr:", lr, "fb:", fb, "ud:", ud, "yaw:", yaw)
                    time.sleep(4)  # wait for takeoff command
                    if(keyboard.is_pressed('space') or keyboard.is_pressed('esc')):
                        break

            if cv2.waitKey(1) & 0xFF == 27 or keyboard.is_pressed('space'):
                break

            # ---- 7. Maintain loop timing ----------------------------------
            # time.sleep(max(0, (1 / loop_hz) - (time.perf_counter() - t0)))

    finally:
        # Cleanly shut down worker threads and the drone
        stop_event.set()
        det_thread.join(timeout=1)
        cam_thread.join(timeout=1)
        try:
            drone.send_rc_control(0, 0, 0, 0)
            drone.land()
        except Exception:
            pass
        frame_reader.stop()
        drone.streamoff()
        drone.end()
        cv2.destroyAllWindows()

# --------------------------------------------------------------------------- #
# Run as script                                                               #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":

    #if not torch.cuda.is_available():
        #raise RuntimeError("CUDA GPU is not available! Please run on a machine with a supported GPU.")

    # Launch the main drone loop in its own thread so the Flask server can
    # continue serving frames concurrently
    drone_thread = threading.Thread(target=run_drone, daemon=False)
    drone_thread.start()

    # Start the Flask web server on the main thread
    app.run(host='0.0.0.0', port=5001)
