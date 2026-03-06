#!/bin/bash
# KNF Studios GameHub - Full Install Script
# Run ONCE on the Pi via SSH
# Usage: bash /home/pi/kiosk/install_service.sh

echo "=========================================="
echo " KNF Studios - Full Install"
echo "=========================================="

# ── Step 1: Install required packages ─────────────────────────────────────────
echo "[1/6] Installing packages..."
sudo apt install -y onboard python3-tk wireless-tools xdotool
pip3 install websocket-client --break-system-packages
echo "      Done."

# ── Step 2: Configure onboard for kiosk use ───────────────────────────────────
echo "[2/6] Configuring onboard..."
mkdir -p /home/pi/.config/onboard
cat > /home/pi/.config/onboard/onboard.conf << 'EOF'
[main]
layout=Phone
theme=Nightshade
enable-background-transparency=false
EOF
echo "      Done."

# ── Step 3: Set permissions on kiosk scripts ──────────────────────────────────
echo "[3/6] Setting script permissions..."
chmod +x /home/pi/kiosk/gamepad_cursor.py
chmod +x /home/pi/kiosk/hud_overlay.py
chmod +x /home/pi/kiosk/settings_gui.py
chmod +x /home/pi/kiosk/restart_kiosk.sh
chmod +x /home/pi/kiosk/find_wm_class.sh
echo "      Done."

# ── Step 4: Install systemd service ───────────────────────────────────────────
echo "[4/6] Installing systemd kiosk service..."
sudo cp /home/pi/kiosk/knf-kiosk.service /etc/systemd/system/knf-kiosk.service
sudo chmod 644 /etc/systemd/system/knf-kiosk.service
echo "      Done."

# ── Step 5: Configure boot ────────────────────────────────────────────────────
echo "[5/6] Configuring boot settings..."
sudo systemctl daemon-reload
sudo systemctl enable knf-kiosk.service
sudo systemctl set-default multi-user.target
sudo raspi-config nonint do_boot_behaviour B2
echo "      Done."

# ── Step 6: Apply Openbox window rules ────────────────────────────────────────
echo "[6/6] Applying Openbox config..."
mkdir -p /home/pi/.config/openbox
cp /home/pi/kiosk/rc.xml /home/pi/.config/openbox/rc.xml
echo "      Done."

echo ""
echo "=========================================="
echo " All done! Reboot now:"
echo " sudo reboot"
echo ""
echo " After reboot:"
echo " - Kiosk starts automatically"
echo " - Cursor visible, no auto-hide"
echo " - All Chromium windows = 800x450"
echo " - A button click on text field = keyboard"
echo " - Y button = toggle keyboard manually"
echo " - Start button = toggle settings"
echo "=========================================="
