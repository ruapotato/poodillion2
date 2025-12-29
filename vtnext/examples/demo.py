#!/usr/bin/env python3
"""
VTNext Demo - Shows off basic capabilities.

Run with:
    cargo run --manifest-path renderer/Cargo.toml < <(python3 examples/demo.py)

Or for interactive mode:
    python3 examples/demo.py | cargo run --manifest-path renderer/Cargo.toml
"""

import sys
import math
import time

# Add client library to path
sys.path.insert(0, "client-py")

from vtnext import (
    text, rect, line, clear, input_raw, cursor_hide,
)


def main():
    # Setup
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    # Clear to dark background
    print(clear((20, 20, 40, 255)), end="")

    # Draw some rotated text
    for i in range(12):
        angle = i * 30
        x = 400 + math.cos(math.radians(angle)) * 150
        y = 300 + math.sin(math.radians(angle)) * 150
        hue_r = int(127 + 127 * math.sin(math.radians(angle)))
        hue_g = int(127 + 127 * math.sin(math.radians(angle + 120)))
        hue_b = int(127 + 127 * math.sin(math.radians(angle + 240)))
        print(text(f"VTNext", x, y, 1, angle, 1.5, (hue_r, hue_g, hue_b, 255)), end="")

    # Draw title
    print(text("Welcome to VTNext!", 300, 50, 2, 0, 2.0, (255, 255, 255, 255)), end="")
    print(text("Next-generation terminal rendering", 280, 90, 2, 0, 1.0, (180, 180, 180, 255)), end="")

    # Draw some shapes
    print(rect(50, 400, 200, 100, 0, 15, (255, 100, 100, 200), True), end="")
    print(rect(250, 420, 200, 100, 0, -10, (100, 255, 100, 200), True), end="")
    print(rect(450, 400, 200, 100, 0, 5, (100, 100, 255, 200), True), end="")

    # Draw lines
    for i in range(20):
        x1 = 700
        y1 = 100 + i * 25
        x2 = 900
        y2 = 100 + (19 - i) * 25
        intensity = int(255 * (i / 19))
        print(line(x1, y1, x2, y2, 0, 2, (intensity, 255 - intensity, 128, 255)), end="")

    # Features list
    features = [
        "Arbitrary text positioning",
        "Text rotation & scaling",
        "Z-depth layering",
        "Alpha blending",
        "Shape primitives",
        "Game-engine input model",
        "Raw key up/down events",
        "Mouse tracking",
    ]

    for i, feature in enumerate(features):
        y = 500 + i * 25
        print(text(f"  {feature}", 50, y, 1, 0, 1.0, (200, 200, 255, 255)), end="")

    sys.stdout.flush()

    # Keep running
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
