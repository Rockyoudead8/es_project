#!/usr/bin/env python3
"""Headless check of manual control: fake odometry in, mode/manual commands in, /camo/cmd_vel out (no Gazebo needed).
Run with the mission node up:  ros2 run camo_ros mission_node --ros-args -p autostart:=false   then   python3 test_manual.py"""
import time, math, rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import String

rclpy.init(); n = Node("test_manual")
odom = n.create_publisher(Odometry, "/camo/odom", 10)
man = n.create_publisher(Twist, "/camo/manual_cmd", 10)
mode = n.create_publisher(String, "/camo/mode_cmd", 10)
last = {"cmd": None, "status": ""}
n.create_subscription(Twist, "/camo/cmd_vel", lambda m: last.update(cmd=(m.linear.x, m.linear.y, m.linear.z, m.angular.z)), 10)
n.create_subscription(String, "/camo/status", lambda m: last.update(status=m.data), 10)
S = dict(x=0.0, y=0.0, z=10.0, yaw=0.0)

def spin(sec, move=None):
    t = time.time() + sec
    while time.time() < t:
        o = Odometry(); o.pose.pose.position.x, o.pose.pose.position.y, o.pose.pose.position.z = S["x"], S["y"], S["z"]
        o.pose.pose.orientation.z, o.pose.pose.orientation.w = math.sin(S["yaw"] / 2), math.cos(S["yaw"] / 2)
        odom.publish(o)
        if move: man.publish(move)
        rclpy.spin_once(n, timeout_sec=0.05)

def tw(x=0, y=0, z=0, w=0):
    t = Twist(); t.linear.x, t.linear.y, t.linear.z, t.angular.z = map(float, (x, y, z, w)); return t

def send(m):
    mode.publish(String(data=m)); spin(0.4)

ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name, last["cmd"], "|", last["status"])

spin(1.5)
send("manual"); spin(0.3, tw(3, 1, 1, 0.5)); check("manual passes velocity", last["cmd"] == (3.0, 1.0, 1.0, 0.5))
spin(1.6);                                    check("dead-man timeout -> hover", last["cmd"] == (0.0, 0.0, 0.0, 0.0))
S["z"] = 1.0; S["x"] = 0.0
spin(0.3, tw(0, 0, -2));                      check("won't descend below floor", last["cmd"][2] >= 0.0)
S["z"] = 10.0; S["x"] = 111.0
spin(0.3, tw(4, 0, 0));                       check("area bound blocks outward motion", abs(last["cmd"][0]) < 1e-6)
spin(0.3, tw(-4, 0, 0));                      check("area bound allows inward motion", last["cmd"][0] < -3.9)
S["x"] = 0.0; S["yaw"] = math.pi / 2; S["x"] = 111.0
spin(0.3, tw(0, -4, 0));                      check("bound is evaluated in world frame (yaw 90deg, strafe right = +x blocked)", abs(last["cmd"][1]) < 1e-6)
spin(0.3, tw(0, 4, 0));                       check("...and strafe left (= -x, inward) allowed", last["cmd"][1] > 3.9)
S.update(x=0.0, yaw=0.0)
send("auto"); spin(0.4, tw(3, 0, 0));          check("auto from WAIT stays idle (no start yet)", last["status"].startswith("WAIT"))
send("start");                                 check("start -> TAKEOFF", last["status"].startswith("TAKEOFF"))
send("manual"); check("manual mid-mission", last["status"].startswith("MANUAL"))
send("auto");   check("auto resumes mission", last["status"].startswith("TAKEOFF") or last["status"].startswith("SEARCH"))
S.update(x=40.0, y=40.0)
send("rtl");    check("rtl (turns/flies home)", last["status"].startswith("RTL") and last["cmd"][3] != 0)
print("ALL PASS" if ok else "SOME FAILED"); rclpy.shutdown()
