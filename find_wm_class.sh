#!/bin/bash
# KNF Studios - Find Chromium WM_CLASS
# Run this WHILE Chromium is open on screen.
# Usage: bash /home/pi/kiosk/find_wm_class.sh
#
# This tells you the exact class name Openbox sees for Chromium windows.
# Use that name in rc.xml if windows are still not being resized correctly.

echo "========================================"
echo " KNF Studios - Find Chromium WM_CLASS"
echo "========================================"
echo ""
echo "Looking for all open Chromium windows..."
echo ""

export DISPLAY=:0

# Get all window IDs for chromium
WIN_IDS=$(xdotool search --class chromium 2>/dev/null)
WIN_IDS2=$(xdotool search --class Chromium 2>/dev/null)
WIN_IDS3=$(xdotool search --name chromium 2>/dev/null)

ALL_IDS=$(echo -e "$WIN_IDS\n$WIN_IDS2\n$WIN_IDS3" | sort -u | grep -v '^$')

if [ -z "$ALL_IDS" ]; then
    echo "No Chromium windows found. Make sure Chromium is running."
    echo "Run: startx  then try again from SSH."
    exit 1
fi

echo "Found windows. Getting WM_CLASS for each:"
echo ""

for ID in $ALL_IDS; do
    echo "Window ID: $ID"
    xprop -id $ID WM_CLASS 2>/dev/null
    xprop -id $ID WM_NAME 2>/dev/null
    echo "---"
done

echo ""
echo "========================================"
echo " Copy the WM_CLASS value above."
echo " It looks like: WM_CLASS = \"name\", \"ClassName\""
echo " Use the SECOND value (ClassName) in rc.xml"
echo " inside <application class=\"ClassName\">"
echo "========================================"
