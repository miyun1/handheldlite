#!/usr/bin/env python3
"""
KNF Studios GameHub - Settings Overlay Launcher
Launches the gamepad-controlled settings GUI.
"""
import subprocess
import os

os.environ['DISPLAY'] = ':0'

subprocess.Popen(['python3', '/home/pi/kiosk/settings_gui.py'])
