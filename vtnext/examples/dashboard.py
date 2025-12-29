#!/usr/bin/env python3
"""
VTNext Dashboard Demo - System monitoring style dashboard.
"""

import sys
import math
import time
import random

sys.path.insert(0, "client-py")

from vtnext import (
    text, rect, circle, line, arc, rounded_rect, polygon,
    clear, input_raw, cursor_hide
)


class Graph:
    def __init__(self, x, y, width, height, title, color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title
        self.color = color
        self.data = [0] * 60
        self.value = 0

    def update(self, value):
        self.value = value
        self.data.append(value)
        if len(self.data) > 60:
            self.data.pop(0)

    def draw(self):
        cmds = []

        # Background
        cmds.append(rounded_rect(self.x, self.y, self.width, self.height, 8, 0, (30, 40, 60, 255), True))

        # Title
        cmds.append(text(self.title, self.x + 10, self.y + 8, 1, 0, 0.9, (200, 210, 230, 255)))

        # Current value
        cmds.append(text(f"{self.value:.1f}%", self.x + self.width - 60, self.y + 8, 1, 0, 0.9, self.color))

        # Graph area
        graph_x = self.x + 10
        graph_y = self.y + 35
        graph_w = self.width - 20
        graph_h = self.height - 45

        # Grid lines
        for i in range(5):
            y = graph_y + graph_h * i / 4
            cmds.append(line(graph_x, y, graph_x + graph_w, y, 0, 1, (50, 60, 80, 100)))

        # Data line
        if len(self.data) > 1:
            points = []
            for i, val in enumerate(self.data):
                px = graph_x + (i / 59) * graph_w
                py = graph_y + graph_h - (val / 100) * graph_h
                points.append((px, py))

            # Draw as connected lines
            for i in range(len(points) - 1):
                cmds.append(line(
                    points[i][0], points[i][1],
                    points[i + 1][0], points[i + 1][1],
                    1, 2, self.color
                ))

            # Fill area under curve
            fill_points = [(graph_x, graph_y + graph_h)] + points + [(graph_x + graph_w, graph_y + graph_h)]
            r, g, b, _ = self.color
            cmds.append(polygon(fill_points, 0, (r, g, b, 50), True))

        return "".join(cmds)


class GaugeWidget:
    def __init__(self, cx, cy, radius, title, color):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.title = title
        self.color = color
        self.value = 0

    def update(self, value):
        self.value = value

    def draw(self):
        cmds = []

        # Background arc
        cmds.append(arc(self.cx, self.cy, self.radius, 135, 405, 0, 15, (40, 50, 70, 255)))

        # Value arc
        end_angle = 135 + (self.value / 100) * 270
        cmds.append(arc(self.cx, self.cy, self.radius, 135, end_angle, 1, 15, self.color))

        # Center
        cmds.append(circle(self.cx, self.cy, self.radius - 25, 2, (25, 35, 55, 255), True))

        # Value text
        cmds.append(text(f"{self.value:.0f}%", self.cx - 25, self.cy - 10, 3, 0, 1.5, (255, 255, 255, 255)))

        # Title
        cmds.append(text(self.title, self.cx - len(self.title) * 4, self.cy + 20, 3, 0, 0.8, (150, 160, 180, 255)))

        return "".join(cmds)


def main():
    print(input_raw(), end="")
    print(cursor_hide(), end="")
    sys.stdout.flush()

    # Create widgets
    cpu_graph = Graph(20, 80, 480, 180, "CPU Usage", (100, 200, 255, 255))
    mem_graph = Graph(520, 80, 480, 180, "Memory", (255, 150, 100, 255))
    net_graph = Graph(20, 280, 480, 180, "Network I/O", (100, 255, 150, 255))
    disk_graph = Graph(520, 280, 480, 180, "Disk Activity", (255, 200, 100, 255))

    cpu_gauge = GaugeWidget(150, 560, 80, "CPU", (100, 200, 255, 255))
    mem_gauge = GaugeWidget(350, 560, 80, "RAM", (255, 150, 100, 255))
    net_gauge = GaugeWidget(550, 560, 80, "NET", (100, 255, 150, 255))
    disk_gauge = GaugeWidget(750, 560, 80, "DISK", (255, 200, 100, 255))

    # Simulated data
    cpu_base = 30
    mem_base = 55
    net_base = 20
    disk_base = 15

    try:
        while True:
            t = time.time()

            # Generate fake data with some variation
            cpu = cpu_base + 20 * math.sin(t * 0.5) + random.uniform(-5, 5)
            mem = mem_base + 10 * math.sin(t * 0.3) + random.uniform(-2, 2)
            net = net_base + 30 * abs(math.sin(t * 0.8)) + random.uniform(-10, 10)
            disk = disk_base + 15 * abs(math.sin(t * 0.2)) + random.uniform(-5, 5)

            cpu = max(0, min(100, cpu))
            mem = max(0, min(100, mem))
            net = max(0, min(100, net))
            disk = max(0, min(100, disk))

            # Update widgets
            cpu_graph.update(cpu)
            mem_graph.update(mem)
            net_graph.update(net)
            disk_graph.update(disk)

            cpu_gauge.update(cpu)
            mem_gauge.update(mem)
            net_gauge.update(net)
            disk_gauge.update(disk)

            # Draw
            print(clear((20, 25, 40, 255)), end="")

            # Title bar
            print(rounded_rect(10, 10, 1004, 50, 8, 0, (30, 40, 60, 255), True), end="")
            print(text("VTNext System Dashboard", 20, 22, 1, 0, 1.5, (255, 255, 255, 255)), end="")

            # Status indicator
            print(circle(980, 35, 8, 2, (100, 255, 100, 255), True), end="")
            print(text("LIVE", 940, 28, 2, 0, 0.8, (100, 255, 100, 255)), end="")

            # Widgets
            print(cpu_graph.draw(), end="")
            print(mem_graph.draw(), end="")
            print(net_graph.draw(), end="")
            print(disk_graph.draw(), end="")

            print(cpu_gauge.draw(), end="")
            print(mem_gauge.draw(), end="")
            print(net_gauge.draw(), end="")
            print(disk_gauge.draw(), end="")

            # Footer
            print(text(f"Uptime: {int(t) // 3600}h {(int(t) // 60) % 60}m {int(t) % 60}s", 20, 720, 1, 0, 0.8, (100, 110, 130, 255)), end="")

            sys.stdout.flush()
            time.sleep(0.1)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
