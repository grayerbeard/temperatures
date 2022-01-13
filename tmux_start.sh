#!/bin/bash
cd /home/pi/code
tmux new-session -d -s ctrl 'python3 /home/pi/code/thrm19.py'
