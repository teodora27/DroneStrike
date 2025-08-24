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
from ultralytics import YOLO
from djitellopy import Tello

# --------------------------------------------------------------------------- #
# 1.  Model‑loader                                                            #
# --------------------------------------------------------------------------- #

def load_detector(model_path: str = "yolov8n.pt", imgsz: int = 416, prefer_gpu: bool = True) -> YOLO:
    """Return a ready‑to‑run YOLOv8 detector on CPU or GPU."""
    model = YOLO(model_path)
    model.to("cuda" if prefer_gpu and torch.cuda.is_available() else "cpu")
    model.fuse()
    model.imgsz = imgsz
    return model

# --------------------------------------------------------------------------- #
# 2.  Main flight loop                                                        #
# --------------------------------------------------------------------------- #

def run_drone(detector: YOLO,
              detect_hz: int = 10,
              loop_hz: int = 20,
              speed_xy: int = 50,
              speed_z: int = 50,
              speed_yaw: int = 50) -> None:

    FONT, FPS_SMOOTH = cv2.FONT_HERSHEY_SIMPLEX, 30

    # ---------------- Overlay helpers -------------------------------------
    def overlay_telemetry(frame, batt, alt, fps, mode, counter):
        header = {0: "AUTO OFF", 1: "SEARCHING…", 2: f"CHASE MODE ({counter})"}[mode]
        lines = [header,
                 f"BAT  {batt:>3}%",
                 f"ALT  {alt:>3} cm",
                 f"FPS  {fps:>4.1f}",
                 "HELP W/S A/D I/K J/L 0=AUTO SPACE=LAND"]
        for i, txt in enumerate(lines):
            cv2.putText(frame, txt, (10, 30 + i * 25), FONT, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    def overlay_dets(frame, dets, chase_pt=None):
        h, w = frame.shape[:2]
        largest = person_box
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
        # red chase point
        if chase_pt is not None:
            cx, cy = chase_pt
            cv2.circle(frame, (int(cx), int(cy)), 8, (0, 0, 255), -1)

    # ---------------- Drone setup -----------------------------------------
    drone = Tello()
    drone.connect()
    drone.streamon()
    frame_reader = drone.get_frame_read()
    print("Drone connected:", drone.get_battery(), "% battery")  
    drone.takeoff()

    # ---------------- Loop state ------------------------------------------
    fps_times = deque(maxlen=FPS_SMOOTH)
    last_detect = 0.0
    detections = []

    autopilot = False
    key0_prev = False

    chase_counter = 0         # frames left until we drop back to search
    last_xmid = 0.5           # last seen x‑ce   ntre (norm)
    last_ytop = 0.5           # last seen top‐y (norm)

    try:
        while True:
            t0 = time.perf_counter()

            # ---- 0. Toggle autopilot with key "0" ------------------------
            key0_curr = keyboard.is_pressed('0')
            if key0_curr and not key0_prev:
                autopilot = not autopilot
                print("AUTOPILOT", "ON" if autopilot else "OFF")
            key0_prev = key0_curr

            # ---- 1. Grab frame -------------------------------------------
            frame = frame_reader.frame
            if frame is None:
                continue
            fh, fw = frame.shape[:2]

            # ---- 2. Detection (<= detect_hz) -----------------------------
            now = time.perf_counter()
            person_box = None
            if now - last_detect >= 1 / detect_hz:
                results = detector(frame, verbose=False)[0]
                detections.clear()
                largest_area = 0
                for box, cls_id, conf in zip(results.boxes.xyxy.int().tolist(),
                                             results.boxes.cls.int().tolist(),
                                             results.boxes.conf.tolist()):
                    x1, y1, x2, y2 = box
                    cls_name = detector.names[cls_id]
                    detections.append((x1, y1, x2, y2, cls_name, conf))
                    if cls_name == "person":
                        area = (x2 - x1) * (y2 - y1)
                        if area > largest_area:
                            largest_area = area
                            person_box = (x1, y1, x2, y2)
                last_detect = now

            # ---- 3. Update chase counter & last seen metrics -------------
            if autopilot and person_box is not None:
                x1, y1, x2, y2 = person_box
                last_xmid = ((x1 + x2) / 2) / fw    # norm 0‑1
                last_ytop = y1 / fh                 # norm 0‑1 (top of box)
                chase_counter = 10                 # reset
            elif autopilot and chase_counter > 0:
                chase_counter -= 1

            # ---- 4. Autopilot commands -----------------------------------
            if autopilot:
                if chase_counter > 0:
                    # --- CHASE ---
                    yaw_auto = -speed_yaw if last_xmid < 0.5 else speed_yaw
                    if last_ytop < 0.5:
                        ud_auto = +speed_z   # go down (descend)
                    elif last_ytop > 0.5:
                        ud_auto = -speed_z    # go up (ascend)
                    else:
                        ud_auto = 0
                    mode = 2
                else:
                    # --- SEARCH ---
                    yaw_auto, ud_auto, mode = speed_yaw, 0, 1
            else:
                yaw_auto, ud_auto, mode = 0, 0, 0

            # ---- 5. Manual inputs ---------------------------------------
            lr = (speed_xy if keyboard.is_pressed('d') else -speed_xy if keyboard.is_pressed('a') else 0)
            fb = (3 * speed_xy if (keyboard.is_pressed('w') or (autopilot and chase_counter > 0)) else -3 * speed_xy if keyboard.is_pressed('s') else 0)
            ud_manual = (speed_z if keyboard.is_pressed('i') else -speed_z if keyboard.is_pressed('k') else 0)
            yaw_manual = (speed_yaw if keyboard.is_pressed('l') else -speed_yaw if keyboard.is_pressed('j') else 0)

            ud_cmd = max(-100, min(100, ud_manual + ud_auto))
            yaw_cmd = max(-100, min(100, yaw_manual + yaw_auto))

            drone.send_rc_control(lr, fb, ud_cmd, yaw_cmd)

            # ---- 6. UI & frame display -----------------------------------
            chase_pt_px = (last_xmid * fw, last_ytop * fh) if autopilot and chase_counter > 0 else None
            overlay_dets(frame, detections, chase_pt_px)
            fps_times.append(now)
            fps = ((len(fps_times) - 1) / (fps_times[-1] - fps_times[0]) if len(fps_times) > 1 else 0.0)
            overlay_telemetry(frame, drone.get_battery(), drone.get_height(), fps, mode, chase_counter)

            cv2.imshow("Tello FPV + YOLO", frame)
            if cv2.waitKey(1) & 0xFF == 27 or keyboard.is_pressed('space'):
                break

            # ---- 7. Maintain loop timing ----------------------------------
            time.sleep(max(0, (1 / loop_hz) - (time.perf_counter() - t0)))

    finally:
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

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is not available! Please run on a machine with a supported GPU.")

    run_drone(load_detector("yolov8n.pt"))
