#!/usr/bin/env python3
"""
KNF Studios GameHub - Window Watcher
Monitors for new Chromium windows (e.g. from window.open() game launches)
and forces them to the correct position and size, keeping the HUD visible.

HUD bar = 30px at top
Chromium window area = 800x450 starting at y=30
"""
import subprocess
import time
import os

os.environ['DISPLAY'] = ':0'

# ── Settings ───────────────────────────────────────────────────────────────────
WIN_X      = 0
WIN_Y      = 30     # below the 30px HUD bar
WIN_W      = 800
WIN_H      = 450    # 480 - 30 = 450
POLL_MS    = 0.5    # how often to check for new windows (seconds)
KNOWN_WINS = set()  # track already-processed window IDs

def get_chromium_windows():
    """Returns list of all current Chromium window IDs."""
    try:
        result = subprocess.run(
            ['xdotool', 'search', '--class', 'chromium'],
            capture_output=True, text=True, timeout=2
        )
        ids = result.stdout.strip().split('\n')
        return set(w for w in ids if w.strip())
    except Exception:
        return set()

def get_window_geometry(win_id):
    """Returns (x, y, w, h) of a window."""
    try:
        result = subprocess.run(
            ['xdotool', 'getwindowgeometry', '--shell', win_id],
            capture_output=True, text=True, timeout=2
        )
        data = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                k, v = line.split('=', 1)
                data[k.strip()] = v.strip()
        x = int(data.get('X', 0))
        y = int(data.get('Y', 0))
        w = int(data.get('WIDTH', 0))
        h = int(data.get('HEIGHT', 0))
        return x, y, w, h
    except Exception:
        return 0, 0, 0, 0

def fix_window(win_id):
    """
    Remove window decorations and force correct position/size.
    Called when a new Chromium window is detected.
    """
    try:
        # Remove window decorations (title bar)
        subprocess.run(
            ['xdotool', 'set_window', '--name', '', win_id],
            capture_output=True
        )
        # Move and resize to correct position
        subprocess.run(
            ['xdotool', 'windowmove', win_id, str(WIN_X), str(WIN_Y)],
            capture_output=True
        )
        subprocess.run(
            ['xdotool', 'windowsize', win_id, str(WIN_W), str(WIN_H)],
            capture_output=True
        )
        # Raise it to front
        subprocess.run(
            ['xdotool', 'windowraise', win_id],
            capture_output=True
        )
        print(f'Window Watcher: fixed window {win_id} -> {WIN_X},{WIN_Y} {WIN_W}x{WIN_H}')
    except Exception as e:
        print(f'Window Watcher: error fixing {win_id}: {e}')

def main():
    global KNOWN_WINS
    print('KNF Window Watcher started...')

    # Give Chromium time to open its first window before we start watching
    time.sleep(4)

    # Seed known windows so we don't re-fix the initial window
    KNOWN_WINS = get_chromium_windows()
    print(f'Window Watcher: tracking {len(KNOWN_WINS)} existing window(s)')

    while True:
        current = get_chromium_windows()

        # Find new windows we haven't seen before
        new_wins = current - KNOWN_WINS

        for win_id in new_wins:
            # Small delay to let the window fully open before moving it
            time.sleep(0.3)
            x, y, w, h = get_window_geometry(win_id)
            print(f'Window Watcher: new window {win_id} at {x},{y} {w}x{h}')

            # Only fix if it's not already in the right place
            if x != WIN_X or y != WIN_Y or w != WIN_W or h != WIN_H:
                fix_window(win_id)

        KNOWN_WINS = current
        time.sleep(POLL_MS)

if __name__ == '__main__':
    main()
