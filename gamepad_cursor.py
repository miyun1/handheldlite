#!/usr/bin/env python3
"""
KNF Studios GameHub - Gamepad Cursor Controller

Button Map (Xbox / Logitech F310):
  Left Stick     = Move cursor
  A (BTN_SOUTH)  = Left click  +  auto-show keyboard if text input focused
  B (BTN_EAST)   = Right click (tap) / Go Home (hold 2s)
  X (BTN_WEST)   = Middle click
  Y (BTN_NORTH)  = Manually toggle on-screen keyboard
  Start          = Open settings GUI
  LB (BTN_TL)    = Scroll up   (hold)
  RB (BTN_TR)    = Scroll down (hold)
  D-pad Up/Down  = Scroll up / down (hold)
"""
import evdev
import subprocess
import threading
import time
import os
import urllib.request
import json

os.environ['DISPLAY'] = ':0'

# ── Settings ───────────────────────────────────────────────────────────────────
CURSOR_SPEED      = 8       # pixels per tick
DEADZONE          = 0.15    # ignore stick below this
HOLD_DURATION     = 2.0     # seconds to hold B to go home
SCROLL_DELAY      = 0.08    # seconds between scroll steps
AXIS_MAX          = 32767
CDP_URL           = 'http://localhost:9222'   # Chromium remote debug port
KB_CHECK_DELAY    = 0.4     # seconds after click before checking focus
KB_POLL_INTERVAL  = 1.0     # seconds between auto-hide checks

keyboard_visible  = False
keyboard_lock     = threading.Lock()

# ── Gamepad detection ──────────────────────────────────────────────────────────
def find_gamepad():
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        caps = dev.capabilities()
        name = dev.name.lower()
        skip = ['touch', 'ft5x06', 'edt-ft', 'touchscreen', 'touchpad']
        if any(k in name for k in skip):
            continue
        if evdev.ecodes.EV_KEY in caps and evdev.ecodes.EV_ABS in caps:
            print(f'Gamepad found: {dev.name}')
            return dev
    return None

# ── Mouse actions ──────────────────────────────────────────────────────────────
def move(dx, dy):
    subprocess.run(
        ['xdotool', 'mousemove_relative', '--', str(dx), str(dy)],
        capture_output=True
    )

def click(btn):
    code = '1' if btn == 'left' else '3' if btn == 'right' else '2'
    subprocess.run(['xdotool', 'click', code], capture_output=True)

def scroll(direction):
    btn = '4' if direction == 'up' else '5'
    subprocess.run(['xdotool', 'click', btn], capture_output=True)

def go_home():
    subprocess.run(['xdotool', 'key', 'ctrl+w'], capture_output=True)

def open_settings():
    subprocess.Popen(['python3', '/home/pi/kiosk/settings_gui.py'])

# ── On-screen keyboard ─────────────────────────────────────────────────────────
def show_keyboard():
    global keyboard_visible
    with keyboard_lock:
        if not keyboard_visible:
            subprocess.Popen(['matchbox-keyboard'])
            keyboard_visible = True
            print('Keyboard: shown')

def hide_keyboard():
    global keyboard_visible
    with keyboard_lock:
        if keyboard_visible:
            subprocess.run(['pkill', 'matchbox-keyboard'], capture_output=True)
            keyboard_visible = False
            print('Keyboard: hidden')

def toggle_keyboard():
    if keyboard_visible:
        hide_keyboard()
    else:
        show_keyboard()

# ── CDP: check if a text input is focused in Chromium ─────────────────────────
def is_input_focused():
    """
    Queries Chromium via Chrome DevTools Protocol (CDP).
    Returns True if the currently focused element is a text input.
    Requires: pip3 install websocket-client
    Requires: chromium launched with --remote-debugging-port=9222
    """
    try:
        import websocket  # websocket-client

        # Get list of debuggable tabs
        req  = urllib.request.urlopen(f'{CDP_URL}/json/list', timeout=1)
        tabs = json.loads(req.read())
        if not tabs:
            return False

        # Connect to first tab's websocket
        ws_url = tabs[0].get('webSocketDebuggerUrl', '')
        if not ws_url:
            return False

        ws = websocket.create_connection(ws_url, timeout=2)

        # Ask: is the focused element a text input or textarea?
        js = (
            "var el = document.activeElement;"
            "var tag = el ? el.tagName : '';"
            "var type = el ? (el.type || '') : '';"
            "var editable = el ? el.isContentEditable : false;"
            "(['INPUT','TEXTAREA'].includes(tag) && "
            " !['button','submit','reset','checkbox','radio','file','image'].includes(type.toLowerCase()))"
            " || editable;"
        )
        ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {'expression': js}
        }))
        result  = json.loads(ws.recv())
        ws.close()
        value = result.get('result', {}).get('result', {}).get('value', False)
        return bool(value)

    except Exception as e:
        # CDP not ready yet or Chromium not open — silent fail
        return False

def check_and_show_keyboard():
    """Called in a thread after A button click with a short delay."""
    time.sleep(KB_CHECK_DELAY)
    if is_input_focused():
        show_keyboard()

def keyboard_autohide_loop():
    """Background thread: hides keyboard when focus leaves a text input."""
    while True:
        time.sleep(KB_POLL_INTERVAL)
        if keyboard_visible:
            if not is_input_focused():
                hide_keyboard()

# ── Main controller class ──────────────────────────────────────────────────────
class Controller:
    def __init__(self):
        self.ax         = 0.0
        self.ay         = 0.0
        self.b_time     = None
        self.lb_held    = False
        self.rb_held    = False
        self.dup_held   = False
        self.ddown_held = False

    def norm(self, v):
        return v / AXIS_MAX

    def dz(self, v):
        return 0.0 if abs(v) < DEADZONE else v

    def cursor_loop(self):
        while True:
            dx = self.dz(self.ax)
            dy = self.dz(self.ay)
            if dx or dy:
                move(int(dx * CURSOR_SPEED), int(dy * CURSOR_SPEED))

            if self.lb_held or self.dup_held:
                scroll('up')
                time.sleep(SCROLL_DELAY)
            elif self.rb_held or self.ddown_held:
                scroll('down')
                time.sleep(SCROLL_DELAY)
            else:
                time.sleep(0.016)

    def handle(self, dev):
        for ev in dev.read_loop():
            if ev.type == evdev.ecodes.EV_ABS:
                v = self.norm(ev.value)

                if ev.code == evdev.ecodes.ABS_X:
                    self.ax = v
                elif ev.code == evdev.ecodes.ABS_Y:
                    self.ay = v

                # D-pad as axis
                elif ev.code == evdev.ecodes.ABS_HAT0Y:
                    if ev.value == -1:
                        self.dup_held   = True
                        self.ddown_held = False
                    elif ev.value == 1:
                        self.ddown_held = True
                        self.dup_held   = False
                    else:
                        self.dup_held   = False
                        self.ddown_held = False

            elif ev.type == evdev.ecodes.EV_KEY:
                c   = ev.code
                val = ev.value

                # A — Left click, then check if input focused
                if c == evdev.ecodes.BTN_SOUTH and val == 1:
                    click('left')
                    threading.Thread(
                        target=check_and_show_keyboard,
                        daemon=True
                    ).start()

                # B — Right click (tap) / Go Home (hold 2s)
                elif c == evdev.ecodes.BTN_EAST:
                    if val == 1:
                        self.b_time = time.time()
                    elif val == 0 and self.b_time:
                        held = time.time() - self.b_time
                        go_home() if held >= HOLD_DURATION else click('right')
                        self.b_time = None

                # X — Middle click
                elif c == evdev.ecodes.BTN_WEST and val == 1:
                    click('middle')

                # Y — Manually toggle keyboard
                elif c == evdev.ecodes.BTN_NORTH and val == 1:
                    toggle_keyboard()

                # Start — Open settings GUI
                elif c == evdev.ecodes.BTN_START and val == 1:
                    open_settings()

                # LB — Scroll up
                elif c == evdev.ecodes.BTN_TL:
                    self.lb_held = (val == 1)

                # RB — Scroll down
                elif c == evdev.ecodes.BTN_TR:
                    self.rb_held = (val == 1)

    def run(self):
        # Start keyboard auto-hide watcher
        threading.Thread(
            target=keyboard_autohide_loop,
            daemon=True
        ).start()

        while True:
            dev = find_gamepad()
            if not dev:
                print('No gamepad found. Retrying in 5s...')
                time.sleep(5)
                continue

            t = threading.Thread(target=self.cursor_loop, daemon=True)
            t.start()

            try:
                self.handle(dev)
            except OSError:
                print('Gamepad disconnected. Reconnecting...')
                self.ax = self.ay = 0.0
                self.lb_held = self.rb_held = False
                self.dup_held = self.ddown_held = False
                time.sleep(2)

if __name__ == '__main__':
    print('KNF Studios Gamepad Controller starting...')
    Controller().run()
