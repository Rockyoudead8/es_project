#!/usr/bin/env python3
"""Demo window: annotated drone camera + mission status HUD + keyboard teleop (OpenCV, shows through WSLg).

Click the video window so it has keyboard focus, then fly (keys are case-insensitive):

    W / S   forward / back          A / D   strafe left / right
    R / F   climb / descend         Q / E   yaw left / right
    SPACE   stop (hover)            1 / 2 / 3   speed: slow / medium / fast
    M       toggle MANUAL <-> AUTO  G   start the autonomous mission     H   return to launch
    I       show / hide this help

A movement key switches the drone to MANUAL automatically. Pressing a key sets that axis moving; pressing the
opposite key first cancels it (W while reversing = stop, S while going forward = stop), SPACE stops everything.
pub : /camo/manual_cmd (Twist, body frame), /camo/mode_cmd (String)   sub : /camo/image_annotated, /camo/status
"""
import time, cv2, numpy as np, rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from .common import img_to_np

WIN = "Camouflage Detection - Drone Camera"
SPEEDS = {"1": 2.0, "2": 5.0, "3": 9.0}          # m/s horizontal presets
YAW_RATE = 0.8                                    # rad/s
HELP = ["DRONE CONTROLS (click this window first)",
        "W/S fwd/back   A/D left/right",
        "R/F up/down    Q/E yaw left/right",
        "SPACE stop     1/2/3 speed",
        "M manual/auto  G start mission",
        "H return home  I hide help"]
# key -> (axis index in [vx, vy, vz, wz], direction)
AXES = {"w": (0, +1), "s": (0, -1), "a": (1, +1), "d": (1, -1), "r": (2, +1), "f": (2, -1), "q": (3, +1), "e": (3, -1)}


class Viewer(Node):
    def __init__(self):
        super().__init__("camo_viewer")
        self.img, self.status = None, "waiting..."
        self.dirs = [0, 0, 0, 0]       # latched direction (-1, 0, +1) per axis
        self.spd = SPEEDS["2"]
        self.show_help = True
        self.manual = False            # optimistic local copy of the mission state (status arrives ~1 s late)
        self.mode_sent_t = 0.0
        self.create_subscription(Image, "/camo/image_annotated", lambda m: setattr(self, "img", img_to_np(m)), 1)
        self.create_subscription(String, "/camo/status", lambda m: setattr(self, "status", m.data), 1)
        self.pub_cmd = self.create_publisher(Twist, "/camo/manual_cmd", 10)
        self.pub_mode = self.create_publisher(String, "/camo/mode_cmd", 10)
        self.create_timer(1 / 30, self.draw)
        self.create_timer(0.1, self.publish_cmd)     # 10 Hz keep-alive; the mission node stops the drone if this stops
        cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN, 960, 720)
        try:
            cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)
        except Exception:
            pass

    # ------------------------------------------------------------------ control
    def velocity(self):
        d, s = self.dirs, self.spd
        return [d[0] * s, d[1] * s, d[2] * min(s, 3.0), d[3] * YAW_RATE]

    def publish_cmd(self):
        v = self.velocity()
        t = Twist()
        t.linear.x, t.linear.y, t.linear.z, t.angular.z = map(float, v)
        self.pub_cmd.publish(t)

    def send_mode(self, mode):
        self.pub_mode.publish(String(data=mode))
        self.manual = (mode == "manual")
        self.mode_sent_t = time.time()

    def in_manual(self):
        return self.manual

    def on_key(self, ch):
        if ch in AXES:
            ax, sign = AXES[ch]
            self.dirs[ax] = 0 if self.dirs[ax] == -sign else sign   # opposite key cancels, otherwise go
            self.send_mode("manual")
        elif ch == " ":
            self.dirs = [0, 0, 0, 0]
            self.send_mode("manual")
        elif ch in SPEEDS:
            self.spd = SPEEDS[ch]
        elif ch == "m":
            self.dirs = [0, 0, 0, 0]
            self.send_mode("auto" if self.in_manual() else "manual")
        elif ch == "g":
            self.dirs = [0, 0, 0, 0]
            self.send_mode("start")
        elif ch == "h":
            self.dirs = [0, 0, 0, 0]
            self.send_mode("rtl")
        elif ch == "i":
            self.show_help = not self.show_help

    # ------------------------------------------------------------------ drawing
    def draw(self):
        k = cv2.waitKey(1)
        if k != -1 and 0 <= (k & 0xFF) < 128:
            self.on_key(chr(k & 0xFF).lower())
        if time.time() - self.mode_sent_t > 2.0:      # trust the mission node's status once it has had time to answer
            self.manual = self.status.startswith("MANUAL")
        f = np.zeros((480, 640, 3), np.uint8) if self.img is None else self.img.copy()
        h, w = f.shape[:2]
        cv2.rectangle(f, (0, h - 30), (w, h), (0, 0, 0), -1)
        cv2.putText(f, self.status, (8, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 120), 1, cv2.LINE_AA)
        v = self.velocity()
        mode = "MANUAL" if self.in_manual() else "AUTO"
        col = (0, 200, 255) if self.in_manual() else (0, 255, 120)
        cv2.putText(f, f"{mode}  fwd {v[0]:+.0f}  left {v[1]:+.0f}  up {v[2]:+.0f}  yaw {v[3]:+.1f}  (speed {self.spd:.0f} m/s)",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
        if self.show_help:
            y0 = 44
            ov = f.copy()
            cv2.rectangle(ov, (4, y0 - 16), (320, y0 + 18 * len(HELP) - 8), (0, 0, 0), -1)
            f = cv2.addWeighted(ov, 0.55, f, 0.45, 0)
            for i, line in enumerate(HELP):
                cv2.putText(f, line, (10, y0 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                            (255, 255, 255) if i else (0, 220, 255), 1, cv2.LINE_AA)
        cv2.imshow(WIN, f)


def main():
    rclpy.init(); rclpy.spin(Viewer()); rclpy.shutdown()
