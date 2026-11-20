#!/bin/bash
source /mnt/c/Pdhai/Es-proj/env.sh
cd /tmp
gz sim -s -r --headless-rendering /mnt/c/Pdhai/Es-proj/worlds/savanna.sdf > /tmp/gzsim.log 2>&1 &
GZ=$!
sleep 25
ros2 run ros_gz_bridge parameter_bridge /camo/camera/image@sensor_msgs/msg/Image[gz.msgs.Image > /tmp/bridge.log 2>&1 &
sleep 4
python3 /mnt/c/Pdhai/Es-proj/scripts/snap.py /mnt/c/Pdhai/Es-proj/build/frame0.png
tail -15 /tmp/gzsim.log
kill $GZ; pkill -f parameter_bridge
