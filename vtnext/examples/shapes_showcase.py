#!/usr/bin/env python3
"""
VTNext Shapes Showcase - Demonstrates all shape primitives.
"""

import sys
import math
import time

sys.path.insert(0, "client-py")

from vtnext import (
    text, rect, circle, ellipse, line, arc, polygon, rounded_rect,
    clear, input_raw, cursor_hide
)


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    try:
        t_start = time.time()

        while True:
            t = time.time() - t_start

            print(clear((25, 30, 45, 255)), end="")

            # Title
            print(text("VTNext Shape Primitives", 350, 20, 10, 0, 1.5, (255, 255, 255, 255)), end="")

            # Rectangles
            print(text("Rectangles", 80, 80, 1, 0, 1.0, (150, 150, 200, 255)), end="")
            print(rect(50, 100, 80, 60, 1, 0, (255, 100, 100, 200), True), end="")
            print(rect(150, 100, 80, 60, 1, 15, (100, 255, 100, 200), True), end="")
            print(rect(250, 100, 80, 60, 1, math.sin(t) * 30, (100, 100, 255, 200), True), end="")
            print(rect(350, 100, 80, 60, 1, 0, (255, 255, 100, 200), False), end="")

            # Circles
            print(text("Circles", 530, 80, 1, 0, 1.0, (150, 150, 200, 255)), end="")
            print(circle(520, 140, 30, 1, (255, 150, 100, 255), True), end="")
            print(circle(600, 140, 30, 1, (100, 255, 150, 255), False), end="")
            print(circle(680, 140, 20 + 10 * math.sin(t * 2), 1, (150, 100, 255, 255), True), end="")
            print(circle(760, 140, 30, 1, (255, 255, 255, 100), True), end="")

            # Ellipses
            print(text("Ellipses", 80, 200, 1, 0, 1.0, (150, 150, 200, 255)), end="")
            print(ellipse(100, 260, 40, 25, 1, 0, (255, 200, 100, 255), True), end="")
            print(ellipse(200, 260, 40, 25, 1, 45, (100, 200, 255, 255), True), end="")
            print(ellipse(300, 260, 40, 25, 1, t * 50, (200, 100, 255, 255), True), end="")
            print(ellipse(400, 260, 40, 25, 1, 0, (255, 100, 200, 255), False), end="")

            # Lines
            print(text("Lines", 530, 200, 1, 0, 1.0, (150, 150, 200, 255)), end="")
            for i in range(8):
                angle = i * 45 + t * 30
                x2 = 560 + math.cos(math.radians(angle)) * 40
                y2 = 260 + math.sin(math.radians(angle)) * 40
                hue = i * 45
                r = int(127 + 127 * math.sin(math.radians(hue)))
                g = int(127 + 127 * math.sin(math.radians(hue + 120)))
                b = int(127 + 127 * math.sin(math.radians(hue + 240)))
                print(line(560, 260, x2, y2, 1, 3, (r, g, b, 255)), end="")

            print(line(650, 230, 750, 230, 1, 1, (255, 255, 255, 255)), end="")
            print(line(650, 250, 750, 250, 1, 3, (255, 255, 255, 255)), end="")
            print(line(650, 275, 750, 275, 1, 6, (255, 255, 255, 255)), end="")

            # Arcs
            print(text("Arcs", 80, 320, 1, 0, 1.0, (150, 150, 200, 255)), end="")
            print(arc(120, 400, 50, 0, 270, 1, 8, (255, 100, 150, 255)), end="")
            print(arc(240, 400, 50, t * 50, t * 50 + 180, 1, 10, (100, 255, 200, 255)), end="")
            print(arc(360, 400, 50, 0, 360, 1, 5, (200, 150, 255, 255)), end="")

            # Polygons
            print(text("Polygons", 530, 320, 1, 0, 1.0, (150, 150, 200, 255)), end="")

            # Triangle
            pts = [(560, 360), (600, 440), (520, 440)]
            print(polygon(pts, 1, (255, 200, 100, 255), True), end="")

            # Pentagon
            cx, cy = 680, 400
            pts = []
            for i in range(5):
                angle = math.radians(i * 72 - 90 + t * 20)
                pts.append((cx + 40 * math.cos(angle), cy + 40 * math.sin(angle)))
            print(polygon(pts, 1, (100, 200, 255, 255), True), end="")

            # Star
            cx, cy = 800, 400
            pts = []
            for i in range(10):
                angle = math.radians(i * 36 - 90)
                r = 45 if i % 2 == 0 else 20
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            print(polygon(pts, 1, (255, 255, 100, 255), True), end="")

            # Rounded Rectangles
            print(text("Rounded Rects", 80, 460, 1, 0, 1.0, (150, 150, 200, 255)), end="")
            print(rounded_rect(50, 490, 100, 60, 5, 1, (255, 150, 150, 255), True), end="")
            print(rounded_rect(170, 490, 100, 60, 15, 1, (150, 255, 150, 255), True), end="")
            print(rounded_rect(290, 490, 100, 60, 25, 1, (150, 150, 255, 255), True), end="")
            print(rounded_rect(410, 490, 100, 60, 10, 1, (255, 255, 150, 255), False), end="")

            # Composite shapes
            print(text("Composites", 600, 460, 1, 0, 1.0, (150, 150, 200, 255)), end="")

            # Smiley face
            print(circle(650, 540, 45, 1, (255, 220, 100, 255), True), end="")
            print(circle(635, 525, 8, 2, (80, 60, 40, 255), True), end="")
            print(circle(665, 525, 8, 2, (80, 60, 40, 255), True), end="")
            print(arc(650, 545, 25, 20, 160, 3, 5, (80, 60, 40, 255)), end="")

            # House
            print(rect(760, 520, 60, 50, 1, 0, (150, 100, 80, 255), True), end="")
            pts = [(760, 520), (790, 485), (820, 520)]
            print(polygon(pts, 2, (180, 50, 50, 255), True), end="")
            print(rect(780, 540, 15, 30, 3, 0, (100, 70, 50, 255), True), end="")

            # Tree
            print(rect(895, 540, 10, 30, 1, 0, (120, 80, 50, 255), True), end="")
            print(circle(900, 520, 25, 2, (50, 150, 50, 255), True), end="")

            # Footer
            print(text("Press Ctrl+C to exit", 400, 620, 1, 0, 0.8, (100, 100, 130, 255)), end="")

            sys.stdout.flush()
            time.sleep(0.033)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
