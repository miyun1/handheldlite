#!/bin/bash
# KNF Studios GameHub - Boot Splash Setup
# Run this ONCE on the Pi to install and configure the boot splash screen.
# Usage: bash splash_setup.sh

echo "======================================"
echo " KNF Studios - Boot Splash Setup"
echo "======================================"

# ── Step 1: Install required packages ─────────────────────────────────────────
echo "[1/5] Installing Plymouth and tools..."
sudo apt install -y plymouth plymouth-themes python3-pil fbi

# ── Step 2: Generate splash image with Python ──────────────────────────────────
echo "[2/5] Generating splash image..."
python3 << 'PYEOF'
try:
    from PIL import Image, ImageDraw, ImageFont
    import os

    W, H = 800, 480
    img  = Image.new('RGB', (W, H), color='#0a0a0a')
    draw = ImageDraw.Draw(img)

    # Background gradient effect (manual horizontal lines)
    for y in range(H):
        r = int(10 + (y / H) * 20)
        g = int(10 + (y / H) * 30)
        b = int(10 + (y / H) * 50)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Accent bar at top
    draw.rectangle([0, 0, W, 6], fill='#2E86C1')

    # Accent bar at bottom
    draw.rectangle([0, H - 6, W, H], fill='#2E86C1')

    # Title text
    try:
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 52)
        font_sub   = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub   = font_title
        font_small = font_title

    # Draw title
    title = 'KNF Studios'
    bbox  = draw.textbbox((0, 0), title, font=font_title)
    tw    = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 140), title, font=font_title, fill='#FFFFFF')

    # Draw subtitle
    sub  = 'GameHub Console'
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    sw   = bbox[2] - bbox[0]
    draw.text(((W - sw) // 2, 210), sub, font=font_sub, fill='#2E86C1')

    # Loading bar outline
    bar_x, bar_y, bar_w, bar_h = 250, 340, 300, 12
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                   outline='#2E86C1', width=2)

    # Loading bar fill
    draw.rectangle([bar_x + 2, bar_y + 2, bar_x + bar_w - 2, bar_y + bar_h - 2],
                   fill='#1A5276')

    # Loading text
    loading = 'Starting...'
    bbox    = draw.textbbox((0, 0), loading, font=font_small)
    lw      = bbox[2] - bbox[0]
    draw.text(((W - lw) // 2, 362), loading, font=font_small, fill='#7F8C8D')

    # Save
    os.makedirs('/home/pi/kiosk/splash', exist_ok=True)
    img.save('/home/pi/kiosk/splash/knf_splash.png')
    print('Splash image created: /home/pi/kiosk/splash/knf_splash.png')

except ImportError:
    print('Pillow not available. Installing...')
    import subprocess
    subprocess.run(['pip3', 'install', 'Pillow', '--break-system-packages'])
    print('Run splash_setup.sh again after install.')
PYEOF

# ── Step 3: Create Plymouth theme ─────────────────────────────────────────────
echo "[3/5] Creating Plymouth theme..."
THEME_DIR="/usr/share/plymouth/themes/knf-gamehub"
sudo mkdir -p "$THEME_DIR"

# Theme .plymouth file
sudo tee "$THEME_DIR/knf-gamehub.plymouth" > /dev/null << 'EOF'
[Plymouth Theme]
Name=KNF GameHub
Description=KNF Studios GameHub Console Boot Splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/knf-gamehub
ScriptFile=/usr/share/plymouth/themes/knf-gamehub/knf-gamehub.script
EOF

# Copy splash image to theme directory
sudo cp /home/pi/kiosk/splash/knf_splash.png "$THEME_DIR/splash.png"

# Theme script file
sudo tee "$THEME_DIR/knf-gamehub.script" > /dev/null << 'EOF'
wallpaper_image = Image("splash.png");
screen_width    = Window.GetWidth();
screen_height   = Window.GetHeight();
scaled          = wallpaper_image.Scale(screen_width, screen_height);
sprite          = Sprite(scaled);
sprite.SetX(0);
sprite.SetY(0);
sprite.SetZ(-100);
EOF

# ── Step 4: Set as default Plymouth theme ─────────────────────────────────────
echo "[4/5] Setting KNF GameHub as boot theme..."
sudo plymouth-set-default-theme knf-gamehub
sudo update-initramfs -u

# ── Step 5: Disable boot text / quiet boot ────────────────────────────────────
echo "[5/5] Configuring quiet boot..."
CMDLINE="/boot/firmware/cmdline.txt"
if grep -q "quiet" "$CMDLINE"; then
    echo "Quiet boot already set."
else
    sudo sed -i 's/$/ quiet splash plymouth.ignore-serial-consoles/' "$CMDLINE"
    echo "Quiet boot enabled."
fi

echo ""
echo "======================================"
echo " Splash setup complete!"
echo " Reboot to see your splash screen."
echo " sudo reboot"
echo "======================================"
