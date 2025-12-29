#!/usr/bin/env python3
"""
VTNext Spinning Text Demo - Animated rotating text.
"""

import sys
import math
import time

sys.path.insert(0, "client-py")

from vtnext import text, clear, input_raw, cursor_hide


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    start_time = time.time()
    messages = [
        "VTNext",
        "Next-Gen Terminal",
        "OpenGL Powered",
        "Game Engine Input",
    ]

    try:
        while True:
            t = time.time() - start_time

            # Clear
            r = int(20 + 10 * math.sin(t * 0.5))
            g = int(20 + 10 * math.sin(t * 0.5 + 2))
            b = int(30 + 10 * math.sin(t * 0.5 + 4))
            print(clear((r, g, b, 255)), end="")

            # Center of screen
            cx, cy = 512, 384

            # Orbiting text
            for i, msg in enumerate(messages):
                angle = t * 30 + i * 90  # degrees
                radius = 200 + 50 * math.sin(t * 2 + i)

                x = cx + math.cos(math.radians(angle)) * radius
                y = cy + math.sin(math.radians(angle)) * radius

                # Color cycling
                hue = (angle + t * 50) % 360
                r = int(127 + 127 * math.sin(math.radians(hue)))
                g = int(127 + 127 * math.sin(math.radians(hue + 120)))
                b = int(127 + 127 * math.sin(math.radians(hue + 240)))

                # Rotation matches orbit angle
                rot = angle + 90

                scale = 1.0 + 0.3 * math.sin(t * 3 + i)

                print(text(msg, x, y, i, rot, scale, (r, g, b, 255)), end="")

            # Center text
            center_scale = 2.0 + 0.5 * math.sin(t * 2)
            print(text("VTNext", cx - 80, cy - 20, 10, math.sin(t) * 5, center_scale, (255, 255, 255, 255)), end="")

            # FPS counter
            print(text(f"t={t:.1f}s", 10, 10, 1, 0, 0.8, (100, 100, 100, 255)), end="")

            sys.stdout.flush()
            time.sleep(0.016)  # ~60fps

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
