#!/usr/bin/env python3
"""
KNF Studios GameHub - HUD Overlay
A slim always-on-top status bar at the top of the screen.
Shows: Clock, WiFi signal, Volume, Battery (if PiSugar HAT present)
Screen: 800x480

Layout (800x30px bar at top):
  [  KNF GameHub  |  HH:MM  |  WiFi: ████  |  Vol: 75%  |  BAT: 82%  ]
"""
import tkinter as tk
import subprocess
import time
import threading
import os
import re

os.environ['DISPLAY'] = ':0'

# ── Settings ───────────────────────────────────────────────────────────────────
SCREEN_W     = 800
HUD_H        = 30
HUD_BG       = '#111111'
HUD_FG       = '#FFFFFF'
HUD_ACCENT   = '#2E86C1'
HUD_WARN     = '#E74C3C'
HUD_OK       = '#2ECC71'
FONT_MAIN    = ('Arial', 11, 'bold')
FONT_SMALL   = ('Arial', 10)
UPDATE_MS    = 3000   # refresh every 3 seconds
HAS_PISUGAR  = False  # set True if you have a PiSugar HAT

# ── Data fetchers ──────────────────────────────────────────────────────────────
def get_time():
    return time.strftime('%H:%M')

def get_wifi():
    try:
        result = subprocess.run(
            ['iwconfig', 'wlan0'],
            capture_output=True, text=True, timeout=2
        )
        match = re.search(r'Signal level=(-\d+)', result.stdout)
        if match:
            dbm = int(match.group(1))
            # Convert dBm to percentage
            if dbm <= -100:
                pct = 0
            elif dbm >= -50:
                pct = 100
            else:
                pct = 2 * (dbm + 100)
            bars = get_bars(pct)
            return f'WiFi {bars}', get_wifi_color(pct)
        # Check if connected at all
        if 'ESSID:off' in result.stdout or 'ESSID:"off"' in result.stdout:
            return 'WiFi OFF', HUD_WARN
        return 'WiFi --', HUD_WARN
    except Exception:
        return 'WiFi --', HUD_WARN

def get_bars(pct):
    if pct >= 75:   return '████'
    elif pct >= 50: return '███░'
    elif pct >= 25: return '██░░'
    elif pct > 0:   return '█░░░'
    else:           return '░░░░'

def get_wifi_color(pct):
    if pct >= 50:  return HUD_OK
    elif pct > 20: return '#F39C12'
    else:          return HUD_WARN

def get_volume():
    try:
        result = subprocess.run(
            ['amixer', 'get', 'Master'],
            capture_output=True, text=True, timeout=2
        )
        match = re.search(r'\[(\d+)%\]', result.stdout)
        if match:
            pct = int(match.group(1))
            icon = get_vol_icon(pct)
            return f'{icon} {pct}%', HUD_FG
        return 'Vol --', HUD_FG
    except Exception:
        return 'Vol --', HUD_FG

def get_vol_icon(pct):
    if pct == 0:    return 'VOL X'
    elif pct < 40:  return 'VOL -'
    elif pct < 75:  return 'VOL +'
    else:           return 'VOL ++'

def get_battery():
    if not HAS_PISUGAR:
        return None, None
    try:
        result = subprocess.run(
            ['pisugar-cli', 'get', 'battery'],
            capture_output=True, text=True, timeout=2
        )
        match = re.search(r'(\d+)', result.stdout)
        if match:
            pct = int(match.group(1))
            color = HUD_OK if pct > 30 else ('#F39C12' if pct > 15 else HUD_WARN)
            icon = 'BAT' if pct > 15 else 'LOW'
            return f'{icon} {pct}%', color
        return 'BAT --', HUD_WARN
    except Exception:
        return None, None

def get_bluetooth():
    try:
        result = subprocess.run(
            ['bluetoothctl', 'show'],
            capture_output=True, text=True, timeout=2
        )
        if 'Powered: yes' in result.stdout:
            return 'BT ON', HUD_OK
        return 'BT OFF', HUD_FG
    except Exception:
        return 'BT --', HUD_FG

# ── HUD Window ─────────────────────────────────────────────────────────────────
class HUD:
    def __init__(self, root):
        self.root = root
        root.title('KNF HUD')
        root.geometry(f'{SCREEN_W}x{HUD_H}+0+0')
        root.configure(bg=HUD_BG)

        # Always on top, no decorations
        root.overrideredirect(True)
        root.wm_attributes('-topmost', True)
        root.wm_attributes('-type', 'dock')

        # ── Layout ─────────────────────────────────────────────────────────────
        # Left: branding
        self.lbl_brand = tk.Label(
            root, text='KNF', font=FONT_MAIN,
            bg=HUD_ACCENT, fg=HUD_FG, padx=8
        )
        self.lbl_brand.pack(side=tk.LEFT)

        # Separator
        tk.Label(root, text=' ', bg=HUD_BG, width=1).pack(side=tk.LEFT)

        # Right side items (packed right to left)
        self.lbl_bat  = tk.Label(root, font=FONT_SMALL, bg=HUD_BG, fg=HUD_FG, padx=6)
        self.lbl_bt   = tk.Label(root, font=FONT_SMALL, bg=HUD_BG, fg=HUD_FG, padx=6)
        self.lbl_vol  = tk.Label(root, font=FONT_SMALL, bg=HUD_BG, fg=HUD_FG, padx=6)
        self.lbl_wifi = tk.Label(root, font=FONT_SMALL, bg=HUD_BG, fg=HUD_FG, padx=6)
        self.lbl_time = tk.Label(root, font=FONT_MAIN,  bg=HUD_BG, fg=HUD_FG, padx=10)

        self.lbl_bat.pack(side=tk.RIGHT)
        tk.Label(root, text='|', bg=HUD_BG, fg='#444444').pack(side=tk.RIGHT)
        self.lbl_bt.pack(side=tk.RIGHT)
        tk.Label(root, text='|', bg=HUD_BG, fg='#444444').pack(side=tk.RIGHT)
        self.lbl_vol.pack(side=tk.RIGHT)
        tk.Label(root, text='|', bg=HUD_BG, fg='#444444').pack(side=tk.RIGHT)
        self.lbl_wifi.pack(side=tk.RIGHT)
        tk.Label(root, text='|', bg=HUD_BG, fg='#444444').pack(side=tk.RIGHT)
        self.lbl_time.pack(side=tk.RIGHT)

        self.update()

    def update(self):
        # Run data fetching in background thread to avoid freezing UI
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        self.root.after(UPDATE_MS, self.update)

    def _fetch_and_update(self):
        t_text                  = get_time()
        wifi_text, wifi_color   = get_wifi()
        vol_text, vol_color     = get_volume()
        bt_text, bt_color       = get_bluetooth()
        bat_text, bat_color     = get_battery()

        # Schedule UI update on main thread
        self.root.after(0, lambda: self._apply(
            t_text, wifi_text, wifi_color,
            vol_text, vol_color,
            bt_text, bt_color,
            bat_text, bat_color
        ))

    def _apply(self, t, wifi, wifi_c, vol, vol_c, bt, bt_c, bat, bat_c):
        self.lbl_time.config(text=t)
        self.lbl_wifi.config(text=wifi, fg=wifi_c)
        self.lbl_vol.config(text=vol, fg=vol_c)
        self.lbl_bt.config(text=bt, fg=bt_c)

        if bat:
            self.lbl_bat.config(text=bat, fg=bat_c)
        else:
            self.lbl_bat.config(text='')

if __name__ == '__main__':
    print('KNF Studios HUD starting...')
    root = tk.Tk()
    hud = HUD(root)
    root.mainloop()
