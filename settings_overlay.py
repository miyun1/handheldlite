#!/usr/bin/env python3
"""
KNF Studios GameHub - Settings Overlay
Launched when user presses START on the gamepad.
Opens a fullscreen terminal with settings options.
"""
import subprocess
import os

os.environ['DISPLAY'] = ':0'

subprocess.Popen([
    'xterm',
    '-fullscreen',
    '-bg', 'black',
    '-fg', 'white',
    '-fs', '14',
    '-title', 'KNF GameHub Settings',
    '-e', '/home/pi/kiosk/settings_menu.sh'
])
