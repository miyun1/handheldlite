#!/bin/bash
# KNF Studios GameHub - bash_profile
# Auto-starts the kiosk on tty1 (physical screen only, not SSH sessions)

if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  startx -- -nocursor 2>/home/pi/kiosk/startx.log
fi
