#!/usr/bin/env python3
"""
KNF Studios GameHub - Settings GUI
A fullscreen gamepad-controlled settings panel.

Controls:
  D-pad Up/Down  = Navigate menu items
  A (BTN_SOUTH)  = Select / Confirm
  B (BTN_EAST)   = Back / Close
  LB / RB        = Decrease / Increase (on volume screen)
"""
import tkinter as tk
import subprocess
import threading
import time
import os
import re
import evdev

os.environ['DISPLAY'] = ':0'

# ── Theme ──────────────────────────────────────────────────────────────────────
BG      = '#0d0d0d'
BG2     = '#1a1a2e'
ACCENT  = '#2E86C1'
FG      = '#FFFFFF'
FG_DIM  = '#7F8C8D'
SEL_BG  = '#2E86C1'
SEL_FG  = '#FFFFFF'
WARN_FG = '#E74C3C'
OK_FG   = '#2ECC71'
W       = 800
H       = 480

CHROMIUM_CMD = [
    'chromium',
    "--app=https://demogamehub4.knfstudios.com/marketplace/",
    '--no-first-run',
    '--disable-infobars',
    '--noerrdialogs',
    '--disable-translate',
    '--check-for-update-interval=31536000',
    '--enable-gpu-rasterization',
    '--enable-accelerated-video-decode',
    '--remote-debugging-port=9222',
    '--window-position=0,30',
    '--window-size=800,450',
]

# ── Gamepad finder ─────────────────────────────────────────────────────────────
def find_gamepad():
    for path in evdev.list_devices():
        dev  = evdev.InputDevice(path)
        caps = dev.capabilities()
        name = dev.name.lower()
        skip = ['touch', 'ft5x06', 'edt-ft', 'touchscreen', 'touchpad']
        if any(k in name for k in skip):
            continue
        if evdev.ecodes.EV_KEY in caps and evdev.ecodes.EV_ABS in caps:
            return dev
    return None

# ── System helpers ─────────────────────────────────────────────────────────────
def get_volume():
    try:
        r = subprocess.run(['amixer', 'get', 'Master'],
                           capture_output=True, text=True, timeout=2)
        m = re.search(r'\[(\d+)%\]', r.stdout)
        return int(m.group(1)) if m else 50
    except Exception:
        return 50

def set_volume(pct):
    pct = max(0, min(100, pct))
    subprocess.run(['amixer', 'set', 'Master', f'{pct}%'], capture_output=True)
    return pct

def get_wifi_networks():
    try:
        r = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
             'dev', 'wifi', 'list'],
            capture_output=True, text=True, timeout=5
        )
        networks = []
        seen = set()
        for line in r.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 4:
                ssid     = parts[0].strip()
                signal   = parts[1].strip()
                security = parts[2].strip()
                in_use   = '*' in parts[3]
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append({
                        'ssid': ssid, 'signal': signal,
                        'security': security, 'in_use': in_use
                    })
        return networks[:8]
    except Exception:
        return []

def connect_wifi(ssid, password=None):
    try:
        cmd = ['nmcli', 'device', 'wifi', 'connect', ssid]
        if password:
            cmd += ['password', password]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return 'successfully' in r.stdout.lower()
    except Exception:
        return False

def get_bt_devices():
    try:
        r = subprocess.run(['bluetoothctl', 'devices'],
                           capture_output=True, text=True, timeout=3)
        devices = []
        for line in r.stdout.strip().split('\n'):
            parts = line.split(' ', 2)
            if len(parts) == 3:
                devices.append({'mac': parts[1], 'name': parts[2]})
        return devices[:6]
    except Exception:
        return []

def do_shutdown():
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])

def do_restart_kiosk():
    """
    Properly restart the kiosk:
    1. Kill all Chromium processes
    2. Wait for them to fully exit
    3. Relaunch Chromium with the correct flags
    """
    # Kill chromium
    subprocess.run(['pkill', '-f', 'chromium'], capture_output=True)
    time.sleep(2)  # Wait for full exit

    # Relaunch Chromium in background
    subprocess.Popen(CHROMIUM_CMD)
    print('Kiosk restarted.')

# ── Base Screen ────────────────────────────────────────────────────────────────
class Screen:
    def __init__(self, app):
        self.app   = app
        self.frame = tk.Frame(app.root, bg=BG, width=W, height=H)

    def show(self):
        self.frame.place(x=0, y=0, width=W, height=H)
        self.frame.lift()
        self.on_show()

    def hide(self):
        self.frame.place_forget()

    def on_show(self):   pass
    def on_dpad_up(self):   pass
    def on_dpad_down(self): pass
    def on_a(self):      pass
    def on_b(self):      self.app.show_main()
    def on_lb(self):     pass
    def on_rb(self):     pass

# ── Confirm Dialog ─────────────────────────────────────────────────────────────
class ConfirmScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.message    = ''
        self.on_confirm = None
        self.selected   = 0   # 0=No, 1=Yes
        self._build()

    def _build(self):
        self.frame.place_configure()
        self.msg_lbl = tk.Label(
            self.frame, text='',
            font=('Arial', 16), bg=BG, fg=FG,
            wraplength=600, justify=tk.CENTER
        )
        self.msg_lbl.place(relx=0.5, rely=0.35, anchor=tk.CENTER)

        btn_frame = tk.Frame(self.frame, bg=BG)
        btn_frame.place(relx=0.5, rely=0.6, anchor=tk.CENTER)

        self.btn_no  = tk.Label(btn_frame, text='  No  ',
                                font=('Arial', 16, 'bold'),
                                bg=BG2, fg=FG, padx=20, pady=10)
        self.btn_no.pack(side=tk.LEFT, padx=20)

        self.btn_yes = tk.Label(btn_frame, text='  Yes  ',
                                font=('Arial', 16, 'bold'),
                                bg=BG2, fg=FG, padx=20, pady=10)
        self.btn_yes.pack(side=tk.LEFT, padx=20)

        tk.Label(self.frame, text='D-pad Left/Right: choose    A: confirm',
                 font=('Arial', 10), bg=BG, fg=FG_DIM
                 ).place(relx=0.5, rely=0.8, anchor=tk.CENTER)

    def setup(self, message, on_confirm):
        self.message    = message
        self.on_confirm = on_confirm
        self.selected   = 0
        self.msg_lbl.config(text=message)
        self._refresh()

    def _refresh(self):
        self.btn_no.config(bg=SEL_BG  if self.selected == 0 else BG2)
        self.btn_yes.config(bg=SEL_BG if self.selected == 1 else BG2)

    def on_dpad_up(self):
        self.selected = 0 if self.selected == 1 else 1
        self._refresh()

    def on_dpad_down(self):
        self.selected = 0 if self.selected == 1 else 1
        self._refresh()

    def on_a(self):
        if self.selected == 1 and self.on_confirm:
            self.on_confirm()
        else:
            self.app.show_main()

    def on_b(self):
        self.app.show_main()

# ── Main Menu Screen ───────────────────────────────────────────────────────────
class MainMenuScreen(Screen):
    ITEMS = [
        ('WiFi Settings',        'wifi'),
        ('Bluetooth Settings',   'bt'),
        ('Volume Control',       'volume'),
        ('Restart Kiosk',        'restart'),
        ('Shutdown Console',     'shutdown'),
        ('Close Settings',       'close'),
    ]

    def __init__(self, app):
        super().__init__(app)
        self.selected = 0
        self._build()

    def _build(self):
        hdr = tk.Frame(self.frame, bg=ACCENT, height=50)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text='  KNF GameHub  —  Settings',
                 font=('Arial', 16, 'bold'), bg=ACCENT, fg=FG
                 ).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(self.frame,
                 text='D-pad: navigate    A: select    B: close',
                 font=('Arial', 10), bg=BG, fg=FG_DIM
                 ).pack(pady=(6, 0))

        self.item_frame = tk.Frame(self.frame, bg=BG)
        self.item_frame.pack(fill=tk.BOTH, expand=True, padx=60, pady=20)

        self.buttons = []
        for label, _ in self.ITEMS:
            btn = tk.Label(
                self.item_frame, text=f'  {label}',
                font=('Arial', 15, 'bold'), bg=BG2, fg=FG,
                anchor='w', pady=10
            )
            btn.pack(fill=tk.X, pady=4)
            self.buttons.append(btn)

    def on_show(self):
        self._refresh()

    def _refresh(self):
        for i, btn in enumerate(self.buttons):
            btn.config(bg=SEL_BG if i == self.selected else BG2)

    def on_dpad_up(self):
        self.selected = (self.selected - 1) % len(self.ITEMS)
        self._refresh()

    def on_dpad_down(self):
        self.selected = (self.selected + 1) % len(self.ITEMS)
        self._refresh()

    def on_a(self):
        key = self.ITEMS[self.selected][1]
        if key == 'wifi':
            self.app.show_screen('wifi')
        elif key == 'bt':
            self.app.show_screen('bt')
        elif key == 'volume':
            self.app.show_screen('volume')
        elif key == 'restart':
            self.app.screens['confirm'].setup(
                'Restart the kiosk?\nChromium will close and reopen.',
                self._do_restart
            )
            self.app.show_screen('confirm')
        elif key == 'shutdown':
            self.app.screens['confirm'].setup(
                'Shutdown the console?\nAll games will close.',
                do_shutdown
            )
            self.app.show_screen('confirm')
        elif key == 'close':
            self.app.close()

    def _do_restart(self):
        self.app.close()
        threading.Thread(target=do_restart_kiosk, daemon=True).start()

    def on_b(self):
        self.app.close()

# ── Volume Screen ──────────────────────────────────────────────────────────────
class VolumeScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.vol = 50
        self._build()

    def _build(self):
        hdr = tk.Frame(self.frame, bg=ACCENT, height=50)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text='  Volume Control',
                 font=('Arial', 16, 'bold'), bg=ACCENT, fg=FG
                 ).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(self.frame,
                 text='LB / D-pad Down: decrease    RB / D-pad Up: increase    B: back',
                 font=('Arial', 10), bg=BG, fg=FG_DIM).pack(pady=(10, 0))

        self.vol_label = tk.Label(
            self.frame, text='50%',
            font=('Arial', 72, 'bold'), bg=BG, fg=FG
        )
        self.vol_label.pack(pady=20)

        self.bar = tk.Canvas(
            self.frame, width=500, height=30, bg=BG, highlightthickness=0
        )
        self.bar.pack()

        tk.Label(self.frame, text='Press B to go back',
                 font=('Arial', 11), bg=BG, fg=FG_DIM).pack(pady=15)

    def on_show(self):
        self.vol = get_volume()
        self._refresh()

    def _refresh(self):
        self.vol_label.config(text=f'{self.vol}%')
        self.bar.delete('all')
        filled = int(500 * self.vol / 100)
        self.bar.create_rectangle(0, 0, 500, 30, fill=BG2, outline='')
        color = OK_FG if self.vol >= 30 else WARN_FG
        if filled > 0:
            self.bar.create_rectangle(0, 0, filled, 30, fill=color, outline='')
        self.bar.create_text(250, 15, text=f'{self.vol}%',
                             fill=FG, font=('Arial', 12, 'bold'))

    def on_lb(self):
        self.vol = set_volume(self.vol - 5)
        self._refresh()

    def on_rb(self):
        self.vol = set_volume(self.vol + 5)
        self._refresh()

    def on_dpad_up(self):
        self.vol = set_volume(self.vol + 5)
        self._refresh()

    def on_dpad_down(self):
        self.vol = set_volume(self.vol - 5)
        self._refresh()

# ── WiFi Screen ────────────────────────────────────────────────────────────────
class WifiScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.networks = []
        self.selected = 0
        self._build()

    def _build(self):
        hdr = tk.Frame(self.frame, bg=ACCENT, height=50)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text='  WiFi Settings',
                 font=('Arial', 16, 'bold'), bg=ACCENT, fg=FG
                 ).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(self.frame,
                 text='D-pad: navigate    A: connect    B: back',
                 font=('Arial', 10), bg=BG, fg=FG_DIM).pack(pady=(6, 0))

        self.status_lbl = tk.Label(
            self.frame, text='Scanning...',
            font=('Arial', 11), bg=BG, fg=FG_DIM
        )
        self.status_lbl.pack(pady=4)

        self.list_frame = tk.Frame(self.frame, bg=BG)
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=6)
        self.rows = []

    def on_show(self):
        self.status_lbl.config(text='Scanning for networks...', fg=FG_DIM)
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        nets = get_wifi_networks()
        self.frame.after(0, lambda: self._show_networks(nets))

    def _show_networks(self, nets):
        for w in self.rows:
            w.destroy()
        self.rows     = []
        self.networks = nets
        self.selected = 0

        if not nets:
            lbl = tk.Label(self.list_frame, text='No networks found.',
                           font=('Arial', 13), bg=BG, fg=FG_DIM)
            lbl.pack()
            self.rows.append(lbl)
            self.status_lbl.config(text='No networks found.')
            return

        for net in nets:
            mark = '  [connected]' if net['in_use'] else ''
            text = f"  {net['ssid']}{mark}   Signal: {net['signal']}"
            lbl  = tk.Label(
                self.list_frame, text=text,
                font=('Arial', 13), bg=BG2, fg=FG, anchor='w', pady=8
            )
            lbl.pack(fill=tk.X, pady=3)
            self.rows.append(lbl)

        self.status_lbl.config(text=f'{len(nets)} networks found. A to connect.')
        self._refresh()

    def _refresh(self):
        for i, row in enumerate(self.rows):
            row.config(bg=SEL_BG if i == self.selected else BG2)

    def on_dpad_up(self):
        if self.networks:
            self.selected = (self.selected - 1) % len(self.networks)
            self._refresh()

    def on_dpad_down(self):
        if self.networks:
            self.selected = (self.selected + 1) % len(self.networks)
            self._refresh()

    def on_a(self):
        if not self.networks:
            return
        net = self.networks[self.selected]
        if net['in_use']:
            self.status_lbl.config(text=f"Already connected to {net['ssid']}", fg=OK_FG)
            return
        self.status_lbl.config(text=f"Connecting to {net['ssid']}...", fg=FG_DIM)
        threading.Thread(target=self._connect, args=(net['ssid'],), daemon=True).start()

    def _connect(self, ssid):
        ok  = connect_wifi(ssid)
        msg = f'Connected to {ssid}!' if ok else f'Failed to connect to {ssid}'
        clr = OK_FG if ok else WARN_FG
        self.frame.after(0, lambda: self.status_lbl.config(text=msg, fg=clr))

# ── Bluetooth Screen ───────────────────────────────────────────────────────────
class BluetoothScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.devices  = []
        self.selected = 0
        self._build()

    def _build(self):
        hdr = tk.Frame(self.frame, bg=ACCENT, height=50)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text='  Bluetooth Settings',
                 font=('Arial', 16, 'bold'), bg=ACCENT, fg=FG
                 ).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(self.frame,
                 text='D-pad: navigate    A: connect    B: back',
                 font=('Arial', 10), bg=BG, fg=FG_DIM).pack(pady=(6, 0))

        self.status_lbl = tk.Label(
            self.frame, text='Loading...',
            font=('Arial', 11), bg=BG, fg=FG_DIM
        )
        self.status_lbl.pack(pady=4)

        self.list_frame = tk.Frame(self.frame, bg=BG)
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=6)
        self.rows = []

    def on_show(self):
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        devs = get_bt_devices()
        self.frame.after(0, lambda: self._show_devices(devs))

    def _show_devices(self, devs):
        for w in self.rows:
            w.destroy()
        self.rows     = []
        self.devices  = devs
        self.selected = 0

        if not devs:
            lbl = tk.Label(
                self.list_frame,
                text='No paired devices.\nPair via SSH first: bluetoothctl',
                font=('Arial', 13), bg=BG, fg=FG_DIM, justify=tk.CENTER
            )
            lbl.pack(pady=20)
            self.rows.append(lbl)
            self.status_lbl.config(text='No paired devices found.')
            return

        for dev in devs:
            lbl = tk.Label(
                self.list_frame,
                text=f"  {dev['name']}  ({dev['mac']})",
                font=('Arial', 13), bg=BG2, fg=FG, anchor='w', pady=8
            )
            lbl.pack(fill=tk.X, pady=3)
            self.rows.append(lbl)

        self.status_lbl.config(text='A to connect to selected device.')
        self._refresh()

    def _refresh(self):
        for i, row in enumerate(self.rows):
            row.config(bg=SEL_BG if i == self.selected else BG2)

    def on_dpad_up(self):
        if self.devices:
            self.selected = (self.selected - 1) % len(self.devices)
            self._refresh()

    def on_dpad_down(self):
        if self.devices:
            self.selected = (self.selected + 1) % len(self.devices)
            self._refresh()

    def on_a(self):
        if not self.devices:
            return
        dev = self.devices[self.selected]
        self.status_lbl.config(text=f"Connecting to {dev['name']}...", fg=FG_DIM)
        threading.Thread(target=self._connect, args=(dev,), daemon=True).start()

    def _connect(self, dev):
        try:
            r   = subprocess.run(['bluetoothctl', 'connect', dev['mac']],
                                 capture_output=True, text=True, timeout=10)
            ok  = 'successful' in r.stdout.lower()
            msg = f"Connected to {dev['name']}!" if ok else f"Failed: {dev['name']}"
            clr = OK_FG if ok else WARN_FG
            self.frame.after(0, lambda: self.status_lbl.config(text=msg, fg=clr))
        except Exception as e:
            self.frame.after(0, lambda: self.status_lbl.config(
                text=f'Error: {e}', fg=WARN_FG))

# ── App ────────────────────────────────────────────────────────────────────────
class SettingsApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('KNF Settings')
        self.root.geometry(f'{W}x{H}+0+0')
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)
        self.root.wm_attributes('-topmost', True)

        self.screens = {
            'main':    MainMenuScreen(self),
            'volume':  VolumeScreen(self),
            'wifi':    WifiScreen(self),
            'bt':      BluetoothScreen(self),
            'confirm': ConfirmScreen(self),
        }
        self.current_screen = None
        self.show_main()

        threading.Thread(target=self._gamepad_loop, daemon=True).start()

    def show_main(self):
        self.show_screen('main')

    def show_screen(self, name):
        if self.current_screen:
            self.current_screen.hide()
        self.current_screen = self.screens[name]
        self.current_screen.show()

    def close(self):
        self.root.destroy()

    def _gamepad_loop(self):
        dev = find_gamepad()
        if not dev:
            return
        for ev in dev.read_loop():
            if ev.type == evdev.ecodes.EV_ABS:
                if ev.code == evdev.ecodes.ABS_HAT0Y:
                    if ev.value == -1:
                        self.root.after(0, self.current_screen.on_dpad_up)
                    elif ev.value == 1:
                        self.root.after(0, self.current_screen.on_dpad_down)

            elif ev.type == evdev.ecodes.EV_KEY:
                c = ev.code
                if ev.value != 1:
                    continue
                if c == evdev.ecodes.BTN_SOUTH:
                    self.root.after(0, self.current_screen.on_a)
                elif c == evdev.ecodes.BTN_EAST:
                    self.root.after(0, self.current_screen.on_b)
                elif c == evdev.ecodes.BTN_TL:
                    self.root.after(0, self.current_screen.on_lb)
                elif c == evdev.ecodes.BTN_TR:
                    self.root.after(0, self.current_screen.on_rb)
                elif c == evdev.ecodes.BTN_START:
                    self.root.after(0, self.close)

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    print('KNF Settings GUI starting...')
    SettingsApp().run()
