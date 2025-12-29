#!/usr/bin/env python3
"""
VTNext Particle System Demo - Animated particles with physics.
"""

import sys
import math
import time
import random

sys.path.insert(0, "client-py")

from vtnext import text, circle, clear, input_raw, cursor_hide


class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(50, 200)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(1.0, 3.0)
        self.max_life = self.life
        self.size = random.uniform(3, 12)
        self.hue = random.uniform(0, 360)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 100 * dt  # gravity
        self.life -= dt
        return self.life > 0

    def draw(self):
        alpha = int(255 * (self.life / self.max_life))
        r = int(127 + 127 * math.sin(math.radians(self.hue)))
        g = int(127 + 127 * math.sin(math.radians(self.hue + 120)))
        b = int(127 + 127 * math.sin(math.radians(self.hue + 240)))
        return circle(self.x, self.y, self.size * (self.life / self.max_life), 1, (r, g, b, alpha), True)


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    particles = []
    last_time = time.time()
    spawn_timer = 0

    emitter_x = 512
    emitter_y = 300
    emitter_angle = 0

    try:
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Move emitter in a circle
            emitter_angle += dt * 0.5
            emitter_x = 512 + math.cos(emitter_angle) * 150
            emitter_y = 300 + math.sin(emitter_angle * 2) * 100

            # Spawn particles
            spawn_timer += dt
            while spawn_timer > 0.02:
                spawn_timer -= 0.02
                particles.append(Particle(emitter_x, emitter_y))

            # Update particles
            particles = [p for p in particles if p.update(dt)]

            # Limit particles
            if len(particles) > 500:
                particles = particles[-500:]

            # Render
            print(clear((10, 10, 20, 255)), end="")

            # Draw all particles
            for p in particles:
                print(p.draw(), end="")

            # Draw emitter
            print(circle(emitter_x, emitter_y, 8, 2, (255, 255, 255, 255), True), end="")

            # Info
            print(text(f"Particles: {len(particles)}", 10, 10, 10, 0, 0.8, (150, 150, 150, 255)), end="")
            print(text("VTNext Particle System", 10, 30, 10, 0, 1.0, (255, 255, 255, 255)), end="")

            sys.stdout.flush()
            time.sleep(0.016)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
