#!/usr/bin/env python3
"""
VTNext Game Input Demo - Shows game-engine style input handling.

This demonstrates:
- Key down/up events (not just characters)
- Modifier key tracking
- Mouse position and button events
- Real-time input handling
"""

import sys
import os
import select
import time

sys.path.insert(0, "client-py")

from vtnext import (
    text, rect, clear, input_raw, cursor_hide,
)
from vtnext.events import (
    EventParser, KeyDownEvent, KeyUpEvent, KeyCharEvent,
    MouseMoveEvent, MouseDownEvent, MouseUpEvent,
)


def main():
    # Setup
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    # State
    keys_held = set()
    mouse_pos = (0, 0)
    mouse_buttons = set()
    event_log = []

    parser = EventParser()

    # Set stdin to non-blocking
    import fcntl
    fd = sys.stdin.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    try:
        while True:
            # Read input
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.016)
                if ready:
                    data = sys.stdin.buffer.read(4096)
                    if data:
                        events = parser.feed(data.decode('utf-8', errors='replace'))
                        for event in events:
                            # Update state
                            if isinstance(event, KeyDownEvent):
                                keys_held.add(event.keycode)
                                event_log.append(f"KEY DOWN: {event.keycode}")
                            elif isinstance(event, KeyUpEvent):
                                keys_held.discard(event.keycode)
                                event_log.append(f"KEY UP: {event.keycode}")
                            elif isinstance(event, KeyCharEvent):
                                event_log.append(f"CHAR: '{event.char}'")
                            elif isinstance(event, MouseMoveEvent):
                                mouse_pos = (event.x, event.y)
                            elif isinstance(event, MouseDownEvent):
                                mouse_buttons.add(event.button)
                                event_log.append(f"MOUSE DOWN: btn {event.button}")
                            elif isinstance(event, MouseUpEvent):
                                mouse_buttons.discard(event.button)
                                event_log.append(f"MOUSE UP: btn {event.button}")

                            # Keep log manageable
                            if len(event_log) > 15:
                                event_log = event_log[-15:]
            except (BlockingIOError, IOError):
                pass

            # Render
            print(clear((20, 25, 35, 255)), end="")

            # Title
            print(text("VTNext Game Input Demo", 50, 30, 1, 0, 1.5, (255, 255, 255, 255)), end="")
            print(text("Press keys, move mouse, click buttons", 50, 60, 1, 0, 1.0, (150, 150, 150, 255)), end="")

            # Keys held
            print(text("Keys Held:", 50, 120, 1, 0, 1.2, (100, 200, 255, 255)), end="")
            keys_str = ", ".join(f"0x{k:02X}" for k in sorted(keys_held)) or "(none)"
            print(text(keys_str, 50, 150, 1, 0, 1.0, (255, 255, 255, 255)), end="")

            # Mouse position
            print(text("Mouse Position:", 50, 200, 1, 0, 1.2, (100, 200, 255, 255)), end="")
            print(text(f"({mouse_pos[0]:.1f}, {mouse_pos[1]:.1f})", 50, 230, 1, 0, 1.0, (255, 255, 255, 255)), end="")

            # Mouse buttons
            print(text("Mouse Buttons:", 50, 280, 1, 0, 1.2, (100, 200, 255, 255)), end="")
            btns_str = ", ".join(["Left", "Right", "Middle"][b] if b < 3 else f"Btn{b}" for b in sorted(mouse_buttons)) or "(none)"
            print(text(btns_str, 50, 310, 1, 0, 1.0, (255, 255, 255, 255)), end="")

            # Draw mouse cursor indicator
            cx, cy = mouse_pos
            color = (255, 100, 100, 255) if mouse_buttons else (100, 255, 100, 255)
            print(rect(cx - 5, cy - 5, 10, 10, 2, 0, color, True), end="")

            # Event log
            print(text("Event Log:", 400, 120, 1, 0, 1.2, (100, 200, 255, 255)), end="")
            for i, log_entry in enumerate(event_log):
                print(text(log_entry, 400, 150 + i * 22, 1, 0, 0.9, (200, 200, 200, 255)), end="")

            # Instructions
            print(text("Press ESC or Ctrl+C to quit", 50, 550, 1, 0, 1.0, (100, 100, 100, 255)), end="")

            sys.stdout.flush()

            # Check for quit (ESC = 0x29)
            if 0x29 in keys_held:
                break

            time.sleep(0.016)  # ~60fps

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
