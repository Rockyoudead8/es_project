#!/bin/bash
source /mnt/c/Pdhai/Es-proj/env.sh
cd /tmp && python3 /mnt/c/Pdhai/Es-proj/scripts/train_yolo.py ${1:-60}
