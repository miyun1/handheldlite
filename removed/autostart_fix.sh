#!/bin/bash
# KNF Studios GameHub - Auto-startx Fix Script
# Run this ONCE on the Pi via SSH to fix the auto-startx issue
# Usage: bash /home/pi/kiosk/autostart_fix.sh

echo "======================================"
echo " KNF Studios - Auto-startx Fix"
echo "======================================"

# ── Step 1: Fix .bash_profile (strip Windows CRLF line endings) ───────────────
echo "[1/4] Writing clean .bash_profile..."
cat > /home/pi/.bash_profile << 'EOF'
#!/bin/bash
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  startx -- -nocursor 2>/home/pi/kiosk/startx.log
fi
EOF
echo "      Done."

# ── Step 2: Also write .profile as fallback ───────────────────────────────────
echo "[2/4] Writing .profile as fallback..."
cat > /home/pi/.profile << 'EOF'
# KNF Studios GameHub
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  startx -- -nocursor 2>/home/pi/kiosk/startx.log
fi
EOF
echo "      Done."

# ── Step 3: Verify raspi-config autologin is correct ─────────────────────────
echo "[3/4] Checking autologin config..."
if grep -q "autologin-user=pi" /etc/lightdm/lightdm.conf 2>/dev/null; then
    echo "      LightDM found - switching to console autologin instead..."
    sudo raspi-config nonint do_boot_behaviour B2
elif systemctl is-active --quiet getty@tty1; then
    echo "      getty@tty1 is active - good."
    # Check if autologin is configured
    if [ -f /etc/systemd/system/getty@tty1.service.d/autologin.conf ]; then
        echo "      Autologin conf exists - good."
    else
        echo "      Setting up console autologin..."
        sudo raspi-config nonint do_boot_behaviour B2
    fi
else
    echo "      Setting up console autologin..."
    sudo raspi-config nonint do_boot_behaviour B2
fi
echo "      Done."

# ── Step 4: Verify the setup ──────────────────────────────────────────────────
echo "[4/4] Verifying..."
echo ""
echo "  .bash_profile:"
cat /home/pi/.bash_profile
echo ""
echo "  Autologin config:"
cat /etc/systemd/system/getty@tty1.service.d/autologin.conf 2>/dev/null || echo "  (using raspi-config default)"

echo ""
echo "======================================"
echo " Fix complete! Now reboot:"
echo " sudo reboot"
echo ""
echo " After reboot the kiosk should start"
echo " automatically without typing startx."
echo "======================================"
