"""
VTNext client - high-level interface for VTNext applications.
"""

import sys
import os
import select
import threading
from typing import Callable, Optional, List, Tuple
from dataclasses import dataclass

from .commands import (
    text, char, rect, line, clear, viewport,
    query_version, query_size, input_raw, input_normal,
    cursor_hide, cursor_show,
)
from .events import InputEvent, EventParser, parse_event


@dataclass
class Color:
    """RGBA color."""
    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255

    def tuple(self) -> Tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    @classmethod
    def rgb(cls, r: int, g: int, b: int) -> "Color":
        return cls(r, g, b, 255)

    @classmethod
    def rgba(cls, r: int, g: int, b: int, a: int) -> "Color":
        return cls(r, g, b, a)

    @classmethod
    def hex(cls, hex_str: str) -> "Color":
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            return cls(r, g, b, 255)
        elif len(hex_str) == 8:
            r, g, b, a = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), int(hex_str[6:8], 16)
            return cls(r, g, b, a)
        raise ValueError(f"Invalid hex color: {hex_str}")


# Common colors
WHITE = Color(255, 255, 255, 255)
BLACK = Color(0, 0, 0, 255)
RED = Color(255, 0, 0, 255)
GREEN = Color(0, 255, 0, 255)
BLUE = Color(0, 0, 255, 255)
YELLOW = Color(255, 255, 0, 255)
CYAN = Color(0, 255, 255, 255)
MAGENTA = Color(255, 0, 255, 255)


class VTNextClient:
    """
    High-level client for VTNext terminal applications.

    Example:
        client = VTNextClient()
        client.clear(BLACK)
        client.text("Hello, VTNext!", x=100, y=100, color=WHITE)
        client.flush()

        for event in client.events():
            if isinstance(event, KeyDownEvent):
                print(f"Key pressed: {event.keycode}")
    """

    def __init__(
        self,
        stdin=None,
        stdout=None,
        raw_mode: bool = True,
    ):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._buffer: List[str] = []
        self._event_parser = EventParser()
        self._running = False
        self._event_callback: Optional[Callable[[InputEvent], None]] = None

        # Enable raw input mode by default
        if raw_mode:
            self.send(input_raw())
            self.send(cursor_hide())
            self.flush()

    def send(self, command: str) -> None:
        """Buffer a command to be sent."""
        self._buffer.append(command)

    def flush(self) -> None:
        """Send all buffered commands."""
        if self._buffer:
            output = "".join(self._buffer)
            self.stdout.write(output)
            self.stdout.flush()
            self._buffer.clear()

    def clear(self, color: Color = BLACK) -> None:
        """Clear the screen."""
        self.send(clear(color.tuple()))

    def text(
        self,
        content: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        rotation: float = 0,
        scale: float = 1.0,
        color: Color = WHITE,
    ) -> None:
        """Draw text."""
        self.send(text(content, x, y, z, rotation, scale, color.tuple()))

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        z: float = 0,
        rotation: float = 0,
        color: Color = WHITE,
        filled: bool = True,
    ) -> None:
        """Draw a rectangle."""
        self.send(rect(x, y, width, height, z, rotation, color.tuple(), filled))

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        z: float = 0,
        thickness: float = 1.0,
        color: Color = WHITE,
    ) -> None:
        """Draw a line."""
        self.send(line(x1, y1, x2, y2, z, thickness, color.tuple()))

    def read_events(self, timeout: float = 0) -> List[InputEvent]:
        """
        Read available input events (non-blocking by default).

        Args:
            timeout: Seconds to wait for input (0 = non-blocking)

        Returns:
            List of parsed events
        """
        # Check if input is available
        if hasattr(self.stdin, 'fileno'):
            try:
                ready, _, _ = select.select([self.stdin], [], [], timeout)
                if not ready:
                    return []
            except (ValueError, OSError):
                pass

        # Try to read available data
        try:
            if hasattr(self.stdin, 'buffer'):
                # Text mode stdin
                data = self.stdin.read(4096) if timeout > 0 else ""
                if hasattr(self.stdin, 'buffer') and hasattr(self.stdin.buffer, 'read1'):
                    # Non-blocking read
                    raw = self.stdin.buffer.read1(4096)
                    if raw:
                        data = raw.decode('utf-8', errors='replace')
            else:
                data = self.stdin.read(4096)

            if data:
                return self._event_parser.feed(data)
        except (BlockingIOError, IOError):
            pass

        return []

    def on_event(self, callback: Callable[[InputEvent], None]) -> None:
        """Set a callback for input events."""
        self._event_callback = callback

    def run(self) -> None:
        """
        Run the event loop (blocking).

        Calls the event callback for each input event.
        Use on_event() to set the callback before calling run().
        """
        self._running = True

        # Set stdin to non-blocking if possible
        if hasattr(self.stdin, 'fileno'):
            import fcntl
            fd = self.stdin.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        try:
            while self._running:
                events = self.read_events(timeout=0.016)  # ~60fps
                for event in events:
                    if self._event_callback:
                        self._event_callback(event)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the event loop."""
        self._running = False
        self.send(cursor_show())
        self.send(input_normal())
        self.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
