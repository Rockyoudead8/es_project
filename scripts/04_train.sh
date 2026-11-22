#!/bin/bash
source /mnt/c/Users/admin/Desktop/padhai/Es-proj/env.sh
cd /tmp && python3 /mnt/c/Users/admin/Desktop/padhai/Es-proj/scripts/train_yolo.py ${1:-60}
