#!/usr/bin/env python3
"""
Test VTNext terminal rendering with sample data

This script sends sample VTNext commands to test the renderer.
"""

import sys
import os

# Sample VTNext output (from actual BrainhairOS vtn_demo)
SAMPLE_OUTPUT = """
\x1b]vtn;input;raw\x07\x1b]vtn;cursor;hide\x07\x1b]vtn;clear;30;40;60;255\x07\x1b]vtn;text;512;30;1;0;1.0;255;255;255;255;"VTNext Graphics Demo"\x07\x1b]vtn;text;512;60;1;0;1.0;150;150;150;255;"Press Q to quit"\x07\x1b]vtn;rect;50;100;1;120;80;0;255;100;100;200;1\x07\x1b]vtn;rect;190;100;1;120;80;0;100;255;100;200;1\x07\x1b]vtn;rect;330;100;1;120;80;0;100;100;255;200;1\x07\x1b]vtn;rect;50;200;1;120;80;0;255;200;200;255;0\x07\x1b]vtn;rect;190;200;1;120;80;0;200;255;200;255;0\x07\x1b]vtn;rect;330;200;1;120;80;0;200;200;255;255;0\x07\x1b]vtn;circle;550;140;1;40;255;150;50;255;1\x07\x1b]vtn;circle;650;140;1;40;150;255;50;255;1\x07\x1b]vtn;circle;750;140;1;40;50;150;255;255;1\x07\x1b]vtn;line;50;320;450;320;1;1;255;255;255;255\x07\x1b]vtn;line;50;320;250;450;1;1;255;200;100;255\x07\x1b]vtn;line;450;320;250;450;1;1;100;200;255;255\x07\x1b]vtn;circle;500;350;1;25;255;255;0;255;1\x07\x1b]vtn;rrect;550;400;1;180;100;15;100;150;200;220;1\x07\x1b]vtn;rrect;750;400;1;180;100;15;200;100;150;220;1\x07\x1b]vtn;text;130;185;1;0;1.0;200;200;200;255;"Filled Rects"\x07\x1b]vtn;text;130;285;1;0;1.0;200;200;200;255;"Outlined Rects"\x07\x1b]vtn;text;640;200;1;0;1.0;200;200;200;255;"Circles"\x07\x1b]vtn;text;230;470;1;0;1.0;200;200;200;255;"Lines"\x07\x1b]vtn;text;700;520;1;0;1.0;200;200;200;255;"Rounded Rects"\x07\x1b]vtn;text;20;600;1;0;1.0;100;100;100;255;"Frame: 0"\x07
"""


class MockInput:
    """Mock input source that provides sample data once"""
    def __init__(self, data):
        self.data = data
        self.sent = False

    def read(self, size=1024):
        if not self.sent:
            self.sent = True
            return self.data
        return ""


def main():
    # Add parent directory to path to import vtnext_terminal
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from vtnext_terminal import VTNextTerminal

    print("VTNext Terminal Render Test")
    print("============================")
    print("Testing with sample VTNext graphics commands...")
    print("Press ESC or Q to quit")
    print()

    terminal = VTNextTerminal()

    # Parse the sample data directly
    terminal.parse_vtnext(SAMPLE_OUTPUT)

    # Now run the event loop (just for display)
    import pygame
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

        pygame.display.flip()
        terminal.clock.tick(60)

    pygame.quit()
    print("Test complete!")


if __name__ == '__main__':
    main()
