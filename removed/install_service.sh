#!/bin/bash
# KNF Studios GameHub - Full Fix Install Script
# Run ONCE on the Pi via SSH
# Usage: bash /home/pi/kiosk/install_service.sh

echo "=========================================="
echo " KNF Studios - Full Fix Install"
echo "=========================================="

# ── Step 1: Install florence on-screen keyboard ───────────────────────────────
echo "[1/6] Installing florence on-screen keyboard..."
sudo apt install -y florence
echo "      Done."

# ── Step 2: Configure florence for kiosk use ──────────────────────────────────
echo "[2/6] Configuring florence..."
mkdir -p /home/pi/.config/florence
cat > /home/pi/.config/florence/florence.conf << 'EOF'
[window]
decorated=false
task-bar=false
floating=true
resizable=false
auto-hide=true
move-to-input=false
keep-ratio=true
EOF

# Set florence to auto-show on input focus via gsettings
gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true 2>/dev/null || true
echo "      Done."

# ── Step 3: Find real Chromium WM_CLASS and update rc.xml ─────────────────────
echo "[3/6] Checking if Chromium WM_CLASS needs updating..."
echo "      NOTE: After reboot, if windows still don't resize correctly,"
echo "      run this while Chromium is open:"
echo "      DISPLAY=:0 xprop WM_CLASS"
echo "      then click the Chromium window and note the class name."
echo "      Update rc.xml with that class name."
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

# ── Step 6: Copy rc.xml to openbox config ─────────────────────────────────────
echo "[6/6] Applying Openbox window rules..."
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
echo " - Cursor is visible, hides when idle"  
echo " - All Chromium windows = 800x450"
echo " - Tap any text field to show keyboard"
echo "=========================================="
