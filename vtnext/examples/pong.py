#!/usr/bin/env python3
"""
VTNext Pong Game - Classic Pong with game-engine input.
"""

import sys
import math
import time
import os
import select

sys.path.insert(0, "client-py")

from vtnext import (
    text, rect, circle, line, rounded_rect, clear, input_raw, cursor_hide
)
from vtnext.events import EventParser, KeyDownEvent, KeyUpEvent


# Game constants
WIDTH = 1024
HEIGHT = 768
PADDLE_WIDTH = 15
PADDLE_HEIGHT = 100
BALL_SIZE = 12
PADDLE_SPEED = 400
BALL_SPEED = 350


class Game:
    def __init__(self):
        self.paddle1_y = HEIGHT / 2 - PADDLE_HEIGHT / 2
        self.paddle2_y = HEIGHT / 2 - PADDLE_HEIGHT / 2
        self.ball_x = WIDTH / 2
        self.ball_y = HEIGHT / 2
        self.ball_vx = BALL_SPEED
        self.ball_vy = BALL_SPEED * 0.5
        self.score1 = 0
        self.score2 = 0
        self.keys = set()

    def update(self, dt):
        # Paddle 1 (W/S keys)
        if 0x1A in self.keys:  # W
            self.paddle1_y -= PADDLE_SPEED * dt
        if 0x16 in self.keys:  # S
            self.paddle1_y += PADDLE_SPEED * dt

        # Paddle 2 (Up/Down arrows)
        if 0x52 in self.keys:  # Up
            self.paddle2_y -= PADDLE_SPEED * dt
        if 0x51 in self.keys:  # Down
            self.paddle2_y += PADDLE_SPEED * dt

        # Clamp paddles
        self.paddle1_y = max(0, min(HEIGHT - PADDLE_HEIGHT, self.paddle1_y))
        self.paddle2_y = max(0, min(HEIGHT - PADDLE_HEIGHT, self.paddle2_y))

        # Ball movement
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        # Ball collision with top/bottom
        if self.ball_y < BALL_SIZE:
            self.ball_y = BALL_SIZE
            self.ball_vy = -self.ball_vy
        if self.ball_y > HEIGHT - BALL_SIZE:
            self.ball_y = HEIGHT - BALL_SIZE
            self.ball_vy = -self.ball_vy

        # Ball collision with paddles
        # Left paddle
        if (self.ball_x - BALL_SIZE < 50 + PADDLE_WIDTH and
            self.ball_x > 50 and
            self.paddle1_y < self.ball_y < self.paddle1_y + PADDLE_HEIGHT):
            self.ball_x = 50 + PADDLE_WIDTH + BALL_SIZE
            self.ball_vx = abs(self.ball_vx) * 1.05
            # Add spin based on where ball hit paddle
            hit_pos = (self.ball_y - self.paddle1_y) / PADDLE_HEIGHT - 0.5
            self.ball_vy += hit_pos * 200

        # Right paddle
        if (self.ball_x + BALL_SIZE > WIDTH - 50 - PADDLE_WIDTH and
            self.ball_x < WIDTH - 50 and
            self.paddle2_y < self.ball_y < self.paddle2_y + PADDLE_HEIGHT):
            self.ball_x = WIDTH - 50 - PADDLE_WIDTH - BALL_SIZE
            self.ball_vx = -abs(self.ball_vx) * 1.05
            hit_pos = (self.ball_y - self.paddle2_y) / PADDLE_HEIGHT - 0.5
            self.ball_vy += hit_pos * 200

        # Scoring
        if self.ball_x < 0:
            self.score2 += 1
            self.reset_ball(-1)
        if self.ball_x > WIDTH:
            self.score1 += 1
            self.reset_ball(1)

        # Speed limit
        speed = math.sqrt(self.ball_vx ** 2 + self.ball_vy ** 2)
        if speed > 800:
            self.ball_vx = self.ball_vx / speed * 800
            self.ball_vy = self.ball_vy / speed * 800

    def reset_ball(self, direction):
        self.ball_x = WIDTH / 2
        self.ball_y = HEIGHT / 2
        self.ball_vx = BALL_SPEED * direction
        self.ball_vy = BALL_SPEED * 0.5 * (1 if self.ball_vy > 0 else -1)

    def draw(self):
        cmds = []

        # Background
        cmds.append(clear((20, 30, 50, 255)))

        # Center line
        for y in range(0, HEIGHT, 30):
            cmds.append(rect(WIDTH / 2 - 3, y, 6, 15, 0, 0, (60, 80, 120, 255), True))

        # Paddles
        cmds.append(rounded_rect(50, self.paddle1_y, PADDLE_WIDTH, PADDLE_HEIGHT, 5, 1, (100, 200, 255, 255), True))
        cmds.append(rounded_rect(WIDTH - 50 - PADDLE_WIDTH, self.paddle2_y, PADDLE_WIDTH, PADDLE_HEIGHT, 5, 1, (255, 100, 150, 255), True))

        # Ball
        cmds.append(circle(self.ball_x, self.ball_y, BALL_SIZE, 2, (255, 255, 255, 255), True))

        # Ball trail
        trail_x = self.ball_x - self.ball_vx * 0.02
        trail_y = self.ball_y - self.ball_vy * 0.02
        cmds.append(circle(trail_x, trail_y, BALL_SIZE * 0.7, 1, (255, 255, 255, 100), True))

        # Scores
        cmds.append(text(str(self.score1), WIDTH / 4, 60, 10, 0, 4.0, (100, 200, 255, 200)))
        cmds.append(text(str(self.score2), 3 * WIDTH / 4 - 30, 60, 10, 0, 4.0, (255, 100, 150, 200)))

        # Controls
        cmds.append(text("W/S - Player 1", 20, HEIGHT - 60, 10, 0, 0.8, (100, 100, 120, 255)))
        cmds.append(text("Up/Down - Player 2", WIDTH - 180, HEIGHT - 60, 10, 0, 0.8, (100, 100, 120, 255)))
        cmds.append(text("VTNext Pong", WIDTH / 2 - 60, 20, 10, 0, 1.0, (80, 90, 110, 255)))

        return "".join(cmds)


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    game = Game()
    parser = EventParser()
    last_time = time.time()

    # Set non-blocking stdin
    import fcntl
    fd = sys.stdin.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    try:
        while True:
            now = time.time()
            dt = min(now - last_time, 0.1)
            last_time = now

            # Read input
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0)
                if ready:
                    data = sys.stdin.buffer.read(4096)
                    if data:
                        events = parser.feed(data.decode('utf-8', errors='replace'))
                        for event in events:
                            if isinstance(event, KeyDownEvent):
                                game.keys.add(event.keycode)
                            elif isinstance(event, KeyUpEvent):
                                game.keys.discard(event.keycode)
            except (BlockingIOError, IOError):
                pass

            # Update and draw
            game.update(dt)
            print(game.draw(), end="")
            sys.stdout.flush()

            # ESC to quit
            if 0x29 in game.keys:
                break

            time.sleep(0.016)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
