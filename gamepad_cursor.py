#!/usr/bin/env python3
"""
KNF Studios GameHub - Gamepad Cursor Controller
Controls mouse cursor, clicks, scroll, keyboard toggle, and settings.

Button Map (Xbox / Logitech F310):
  A (BTN_SOUTH)  = Left click
  B (BTN_EAST)   = Right click (tap) / Go home (hold 2s)
  X (BTN_WEST)   = Middle click
  Y (BTN_NORTH)  = Toggle on-screen keyboard
  Start          = Open settings overlay
  LB (BTN_TL)    = Scroll up (hold to keep scrolling)
  RB (BTN_TR)    = Scroll down (hold to keep scrolling)
  D-pad Up/Down  = Scroll up / down (hold to keep scrolling)
  Left Stick     = Move cursor
"""
import evdev, subprocess, threading, time, os

CURSOR_SPEED  = 8      # pixels per tick
DEADZONE      = 0.15   # ignore stick below this (0.0 - 1.0)
HOLD_DURATION = 2.0    # seconds to hold B for Go Home
SCROLL_DELAY  = 0.08   # seconds between scroll steps (lower = faster)
AXIS_MAX      = 32767
os.environ['DISPLAY'] = ':0'

keyboard_visible = False

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

def move(dx, dy):
    subprocess.run(['xdotool', 'mousemove_relative', '--', str(dx), str(dy)],
                   capture_output=True)

def click(btn):
    code = '1' if btn == 'left' else '3' if btn == 'right' else '2'
    subprocess.run(['xdotool', 'click', code], capture_output=True)

def scroll(direction):
    btn = '4' if direction == 'up' else '5'
    subprocess.run(['xdotool', 'click', btn], capture_output=True)

def go_home():
    subprocess.run(['xdotool', 'key', 'ctrl+w'], capture_output=True)

def open_settings():
    subprocess.Popen(['python3', '/home/pi/kiosk/settings_overlay.py'])

def toggle_keyboard():
    global keyboard_visible
    if keyboard_visible:
        subprocess.run(['pkill', 'matchbox-keyboard'], capture_output=True)
        keyboard_visible = False
        print('Keyboard hidden')
    else:
        subprocess.Popen(['matchbox-keyboard'])
        keyboard_visible = True
        print('Keyboard shown')

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

                # D-pad as axis (most gamepads)
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

                # A — Left click
                if c == evdev.ecodes.BTN_SOUTH and val == 1:
                    click('left')

                # B — Right click (tap) or Go Home (hold 2s)
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

                # Y — Toggle on-screen keyboard
                elif c == evdev.ecodes.BTN_NORTH and val == 1:
                    toggle_keyboard()

                # Start — Open settings
                elif c == evdev.ecodes.BTN_START and val == 1:
                    open_settings()

                # LB — Scroll up
                elif c == evdev.ecodes.BTN_TL:
                    self.lb_held = (val == 1)

                # RB — Scroll down
                elif c == evdev.ecodes.BTN_TR:
                    self.rb_held = (val == 1)

    def run(self):
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
                print('Gamepad disconnected. Waiting to reconnect...')
                self.ax = self.ay = 0.0
                self.lb_held = self.rb_held = False
                self.dup_held = self.ddown_held = False
                time.sleep(2)

if __name__ == '__main__':
    print('KNF Studios Gamepad Controller starting...')
    Controller().run()
