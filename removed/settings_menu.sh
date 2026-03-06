#!/bin/bash
# KNF Studios GameHub - Settings Menu
# Opened by settings_overlay.py when user presses START on gamepad

while true; do
  clear
  echo '================================'
  echo '   KNF GameHub - Settings'
  echo '================================'
  echo ''
  echo '  1) WiFi Settings'
  echo '  2) Bluetooth Settings'
  echo '  3) Volume Control'
  echo '  4) Restart Kiosk'
  echo '  5) Shutdown Console'
  echo '  6) Close Settings (return to game)'
  echo ''
  read -p '  Select [1-6]: ' choice

  case $choice in
    1)
      nmtui
      ;;
    2)
      bluetoothctl
      ;;
    3)
      echo ''
      echo 'Current volume:'
      amixer get Master
      echo ''
      read -p 'Set volume % (0-100): ' vol
      amixer set Master ${vol}%
      ;;
    4)
      pkill chromium
      sleep 1
      openbox --restart
      break
      ;;
    5)
      sudo shutdown -h now
      ;;
    6)
      break
      ;;
    *)
      echo 'Invalid option. Try again.'
      sleep 1
      ;;
  esac
done

exit 0
