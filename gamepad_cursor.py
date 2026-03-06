#!/usr/bin/env python3
"""
KNF Studios GameHub - Gamepad Cursor Controller

Button Map (Xbox / Logitech F310):
  Left Stick     = Move cursor
  A (BTN_SOUTH)  = Left click  +  auto-show keyboard if text input focused
  B (BTN_EAST)   = Right click (tap) / Go Home (hold 2s)
  X (BTN_WEST)   = Middle click
  Y (BTN_NORTH)  = Toggle on-screen keyboard manually
  Start          = Toggle settings GUI (open if closed, close if open)
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
CURSOR_SPEED     = 8
DEADZONE         = 0.15
HOLD_DURATION    = 2.0
SCROLL_DELAY     = 0.08
AXIS_MAX         = 32767
CDP_URL          = 'http://localhost:9222'
KB_CHECK_DELAY   = 0.5    # seconds after A-click before checking focus
KB_POLL_INTERVAL = 1.5    # seconds between auto-hide checks

# ── Process helpers — always reflect real state via pgrep ──────────────────────
def is_running(name):
    """Check if a process matching name is currently running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', name],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def kill_process(name):
    """Kill all processes matching name."""
    subprocess.run(['pkill', '-f', name], capture_output=True)

# ── Gamepad detection ──────────────────────────────────────────────────────────
def find_gamepad():
    for path in evdev.list_devices():
        dev  = evdev.InputDevice(path)
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

# ── Settings toggle ────────────────────────────────────────────────────────────
def toggle_settings():
    """
    Open settings if not running. Close it if already open.
    Uses pgrep so the check always reflects reality — no flag drift.
    """
    if is_running('settings_gui.py'):
        print('Settings: closing')
        kill_process('settings_gui.py')
    else:
        print('Settings: opening')
        subprocess.Popen(
            ['python3', '/home/pi/kiosk/settings_gui.py'],
            env=dict(os.environ, DISPLAY=':0')
        )

# ── On-screen keyboard (onboard) ───────────────────────────────────────────────
def keyboard_is_open():
    """Always check real process state — never use a flag."""
    return is_running('onboard')

def show_keyboard():
    if not keyboard_is_open():
        print('Keyboard: showing')
        subprocess.Popen(
            ['onboard',
             '--layout=Phone',
             '--size=800x200',
             '--x-position=0',
             '--y-position=280'],
            env=dict(os.environ, DISPLAY=':0')
        )
        time.sleep(0.3)

def hide_keyboard():
    if keyboard_is_open():
        print('Keyboard: hiding')
        kill_process('onboard')

def toggle_keyboard():
    """Y button — toggle keyboard open/closed based on real process state."""
    if keyboard_is_open():
        hide_keyboard()
    else:
        show_keyboard()

# ── CDP: check if text input is focused in Chromium ───────────────────────────
def is_input_focused():
    """
    Query Chromium via Chrome DevTools Protocol.
    Returns True if the focused element is a text input or textarea.
    Requires: pip3 install websocket-client
    Requires: chromium launched with --remote-debugging-port=9222
    """
    try:
        import websocket

        req  = urllib.request.urlopen(f'{CDP_URL}/json/list', timeout=1)
        tabs = json.loads(req.read())
        if not tabs:
            return False

        # Find a page tab with a websocket URL (skip service workers)
        ws_url = None
        for tab in tabs:
            if tab.get('type') == 'page' and tab.get('webSocketDebuggerUrl'):
                ws_url = tab['webSocketDebuggerUrl']
                break
        if not ws_url:
            return False

        ws = websocket.create_connection(ws_url, timeout=2)
        js = (
            "(function(){"
            "  var el = document.activeElement;"
            "  if (!el) return false;"
            "  var tag  = el.tagName.toUpperCase();"
            "  var type = (el.type || '').toLowerCase();"
            "  var skip = ['button','submit','reset','checkbox',"
            "              'radio','file','image','range','color'];"
            "  if (tag === 'TEXTAREA') return true;"
            "  if (tag === 'INPUT' && skip.indexOf(type) === -1) return true;"
            "  if (el.isContentEditable) return true;"
            "  return false;"
            "})()"
        )
        ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {'expression': js}
        }))
        result = json.loads(ws.recv())
        ws.close()
        value  = result.get('result', {}).get('result', {}).get('value', False)
        return bool(value)

    except Exception:
        return False

def check_keyboard_after_click():
    """
    Called in a thread after A button click.
    Waits briefly for browser focus to settle, then shows keyboard if input focused.
    """
    time.sleep(KB_CHECK_DELAY)
    if is_input_focused():
        show_keyboard()

def keyboard_autohide_loop():
    """
    Background thread.
    Hides keyboard automatically when focus leaves a text input.
    """
    while True:
        time.sleep(KB_POLL_INTERVAL)
        try:
            if keyboard_is_open() and not is_input_focused():
                hide_keyboard()
        except Exception:
            pass

# ── Main controller ────────────────────────────────────────────────────────────
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
                elif ev.code == evdev.ecodes.ABS_HAT0Y:
                    if ev.value == -1:
                        self.dup_held = True;   self.ddown_held = False
                    elif ev.value == 1:
                        self.ddown_held = True;  self.dup_held = False
                    else:
                        self.dup_held = False;   self.ddown_held = False

            elif ev.type == evdev.ecodes.EV_KEY:
                c   = ev.code
                val = ev.value

                # A — Left click + check for text input focus
                if c == evdev.ecodes.BTN_SOUTH and val == 1:
                    click('left')
                    threading.Thread(
                        target=check_keyboard_after_click,
                        daemon=True
                    ).start()

                # B — Right click (tap) or Go Home (hold 2s)
                elif c == evdev.ecodes.BTN_EAST:
                    if val == 1:
                        self.b_time = time.time()
                    elif val == 0 and self.b_time:
                        held = time.time() - self.b_time
                        if held >= HOLD_DURATION:
                            hide_keyboard()
                            go_home()
                        else:
                            click('right')
                        self.b_time = None

                # X — Middle click
                elif c == evdev.ecodes.BTN_WEST and val == 1:
                    click('middle')

                # Y — Toggle keyboard
                elif c == evdev.ecodes.BTN_NORTH and val == 1:
                    toggle_keyboard()

                # Start — Toggle settings (open if closed, close if open)
                elif c == evdev.ecodes.BTN_START and val == 1:
                    toggle_settings()

                # LB — Scroll up
                elif c == evdev.ecodes.BTN_TL:
                    self.lb_held = (val == 1)

                # RB — Scroll down
                elif c == evdev.ecodes.BTN_TR:
                    self.rb_held = (val == 1)

    def run(self):
        threading.Thread(target=keyboard_autohide_loop, daemon=True).start()

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
