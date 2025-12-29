#!/usr/bin/env python3
"""
VTNext Analog Clock Demo - Beautiful animated clock.
"""

import sys
import math
import time
from datetime import datetime

sys.path.insert(0, "client-py")

from vtnext import (
    text, circle, line, arc, clear, input_raw, cursor_hide
)


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    cx, cy = 512, 384
    radius = 250

    try:
        while True:
            now = datetime.now()
            hour = now.hour % 12
            minute = now.minute
            second = now.second
            microsecond = now.microsecond

            # Smooth second hand
            smooth_second = second + microsecond / 1_000_000

            # Clear
            print(clear((15, 20, 35, 255)), end="")

            # Outer ring
            print(circle(cx, cy, radius + 10, 0, (40, 50, 80, 255), True), end="")
            print(circle(cx, cy, radius, 0, (20, 25, 45, 255), True), end="")

            # Hour markers
            for i in range(12):
                angle = math.radians(i * 30 - 90)
                inner_r = radius - 30
                outer_r = radius - 10
                x1 = cx + math.cos(angle) * inner_r
                y1 = cy + math.sin(angle) * inner_r
                x2 = cx + math.cos(angle) * outer_r
                y2 = cy + math.sin(angle) * outer_r
                thickness = 6 if i % 3 == 0 else 3
                print(line(x1, y1, x2, y2, 1, thickness, (200, 210, 230, 255)), end="")

            # Minute markers
            for i in range(60):
                if i % 5 != 0:
                    angle = math.radians(i * 6 - 90)
                    inner_r = radius - 15
                    outer_r = radius - 10
                    x1 = cx + math.cos(angle) * inner_r
                    y1 = cy + math.sin(angle) * inner_r
                    x2 = cx + math.cos(angle) * outer_r
                    y2 = cy + math.sin(angle) * outer_r
                    print(line(x1, y1, x2, y2, 1, 1, (100, 110, 130, 255)), end="")

            # Hour hand
            hour_angle = math.radians((hour + minute / 60) * 30 - 90)
            hour_len = radius * 0.5
            hx = cx + math.cos(hour_angle) * hour_len
            hy = cy + math.sin(hour_angle) * hour_len
            print(line(cx, cy, hx, hy, 2, 12, (200, 200, 220, 255)), end="")

            # Minute hand
            min_angle = math.radians((minute + second / 60) * 6 - 90)
            min_len = radius * 0.75
            mx = cx + math.cos(min_angle) * min_len
            my = cy + math.sin(min_angle) * min_len
            print(line(cx, cy, mx, my, 3, 8, (180, 190, 210, 255)), end="")

            # Second hand
            sec_angle = math.radians(smooth_second * 6 - 90)
            sec_len = radius * 0.85
            sx = cx + math.cos(sec_angle) * sec_len
            sy = cy + math.sin(sec_angle) * sec_len
            # Tail
            tail_len = 30
            tx = cx - math.cos(sec_angle) * tail_len
            ty = cy - math.sin(sec_angle) * tail_len
            print(line(tx, ty, sx, sy, 4, 3, (255, 80, 80, 255)), end="")

            # Center cap
            print(circle(cx, cy, 15, 5, (60, 70, 100, 255), True), end="")
            print(circle(cx, cy, 8, 6, (255, 80, 80, 255), True), end="")

            # Digital time
            time_str = now.strftime("%H:%M:%S")
            print(text(time_str, cx - 60, cy + radius + 50, 10, 0, 1.5, (200, 210, 230, 255)), end="")

            # Date
            date_str = now.strftime("%A, %B %d, %Y")
            print(text(date_str, cx - 120, cy + radius + 80, 10, 0, 1.0, (120, 130, 150, 255)), end="")

            # Title
            print(text("VTNext Clock", cx - 70, 30, 10, 0, 1.2, (150, 160, 180, 255)), end="")

            sys.stdout.flush()
            time.sleep(0.016)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
