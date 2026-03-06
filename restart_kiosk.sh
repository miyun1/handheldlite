#!/bin/bash
# KNF Studios GameHub - Restart Kiosk Script
# Called by settings_gui.py when user selects Restart Kiosk
# Runs independently so it survives after settings GUI closes

export DISPLAY=:0

echo "Restarting kiosk..."

# Kill ALL chromium instances
pkill -f chromium
sleep 3

# Make sure it's fully dead
if pgrep -f chromium > /dev/null; then
    pkill -9 -f chromium
    sleep 1
fi

echo "Chromium killed. Relaunching..."

# Relaunch Chromium
chromium \
  --app='https://demogamehub4.knfstudios.com/marketplace/' \
  --no-first-run \
  --disable-infobars \
  --noerrdialogs \
  --disable-translate \
  --check-for-update-interval=31536000 \
  --enable-gpu-rasterization \
  --enable-accelerated-video-decode \
  --remote-debugging-port=9222 \
  --window-position=0,30 \
  --window-size=800,450 &

echo "Kiosk restarted."
