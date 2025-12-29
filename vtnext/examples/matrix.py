#!/usr/bin/env python3
"""
VTNext Matrix Rain Effect - Classic digital rain animation.
"""

import sys
import math
import time
import random

sys.path.insert(0, "client-py")

from vtnext import text, clear, input_raw, cursor_hide


# Matrix characters (katakana + numbers + symbols)
CHARS = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789@#$%^&*"


class Column:
    def __init__(self, x, height):
        self.x = x
        self.y = random.uniform(-height, 0)
        self.speed = random.uniform(100, 400)
        self.length = random.randint(5, 25)
        self.chars = [random.choice(CHARS) for _ in range(self.length)]
        self.height = height
        self.char_height = 20

    def update(self, dt):
        self.y += self.speed * dt

        # Random character changes
        if random.random() < 0.1:
            idx = random.randint(0, self.length - 1)
            self.chars[idx] = random.choice(CHARS)

        # Reset if off screen
        if self.y - self.length * self.char_height > self.height:
            self.y = random.uniform(-self.height * 0.5, 0)
            self.speed = random.uniform(100, 400)
            self.length = random.randint(5, 25)
            self.chars = [random.choice(CHARS) for _ in range(self.length)]

    def draw(self):
        cmds = []
        for i, ch in enumerate(self.chars):
            cy = self.y - i * self.char_height
            if 0 <= cy <= self.height:
                # Brightness fades for trailing characters
                if i == 0:
                    # Head is bright white/green
                    color = (200, 255, 200, 255)
                else:
                    # Fade from bright to dim green
                    fade = max(0, 1 - i / self.length)
                    brightness = int(100 + 155 * fade)
                    alpha = int(100 + 155 * fade)
                    color = (0, brightness, 0, alpha)

                cmds.append(text(ch, self.x, cy, 1, 0, 1.0, color))
        return "".join(cmds)


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    width = 1024
    height = 768
    char_width = 18

    # Create columns
    columns = []
    for x in range(0, width, char_width):
        columns.append(Column(x, height))
        # Stagger start positions
        columns[-1].y = random.uniform(-height, height)

    last_time = time.time()

    try:
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Update
            for col in columns:
                col.update(dt)

            # Draw
            print(clear((0, 5, 0, 255)), end="")

            for col in columns:
                print(col.draw(), end="")

            # Title (subtle)
            print(text("VTNext Matrix", width // 2 - 70, height - 30, 10, 0, 1.0, (0, 60, 0, 255)), end="")

            sys.stdout.flush()
            time.sleep(0.033)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
