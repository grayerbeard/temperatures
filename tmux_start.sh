#!/bin/bash
cd /home/pi/temperatures
tmux new-session -d -s ctrl 'python3 /home/pi/temperatures/temperatures.py'
