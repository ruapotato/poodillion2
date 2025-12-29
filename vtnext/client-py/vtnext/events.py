"""
VTNext input events - parsing escape sequences from the terminal.
"""

from dataclasses import dataclass
from typing import Optional, Union
import re


# Modifier key masks
SHIFT_L = 0x0001
SHIFT_R = 0x0002
CTRL_L = 0x0004
CTRL_R = 0x0008
ALT_L = 0x0010
ALT_R = 0x0020
META_L = 0x0040
META_R = 0x0080
CAPS_LOCK = 0x0100
NUM_LOCK = 0x0200


@dataclass
class Modifiers:
    """Modifier key state."""
    raw: int

    @property
    def shift(self) -> bool:
        return bool(self.raw & (SHIFT_L | SHIFT_R))

    @property
    def ctrl(self) -> bool:
        return bool(self.raw & (CTRL_L | CTRL_R))

    @property
    def alt(self) -> bool:
        return bool(self.raw & (ALT_L | ALT_R))

    @property
    def meta(self) -> bool:
        return bool(self.raw & (META_L | META_R))

    @property
    def caps_lock(self) -> bool:
        return bool(self.raw & CAPS_LOCK)

    @property
    def num_lock(self) -> bool:
        return bool(self.raw & NUM_LOCK)


@dataclass
class KeyDownEvent:
    """Key pressed event."""
    keycode: int
    scancode: int
    modifiers: Modifiers
    timestamp: int


@dataclass
class KeyUpEvent:
    """Key released event."""
    keycode: int
    scancode: int
    modifiers: Modifiers
    timestamp: int


@dataclass
class KeyRepeatEvent:
    """Key repeat event."""
    keycode: int
    scancode: int
    modifiers: Modifiers
    timestamp: int


@dataclass
class KeyCharEvent:
    """Character input event."""
    codepoint: int
    modifiers: Modifiers
    timestamp: int

    @property
    def char(self) -> str:
        return chr(self.codepoint)


@dataclass
class MouseDownEvent:
    """Mouse button pressed."""
    button: int  # 0=left, 1=right, 2=middle
    x: float
    y: float
    modifiers: Modifiers
    timestamp: int


@dataclass
class MouseUpEvent:
    """Mouse button released."""
    button: int
    x: float
    y: float
    modifiers: Modifiers
    timestamp: int


@dataclass
class MouseMoveEvent:
    """Mouse moved."""
    x: float
    y: float
    dx: float
    dy: float
    modifiers: Modifiers
    timestamp: int


@dataclass
class ScrollEvent:
    """Mouse scroll/wheel."""
    dx: float
    dy: float
    x: float
    y: float
    modifiers: Modifiers
    timestamp: int


@dataclass
class FocusEvent:
    """Window focus changed."""
    focused: bool


@dataclass
class ResizeEvent:
    """Window resized."""
    width: float
    height: float


InputEvent = Union[
    KeyDownEvent, KeyUpEvent, KeyRepeatEvent, KeyCharEvent,
    MouseDownEvent, MouseUpEvent, MouseMoveEvent, ScrollEvent,
    FocusEvent, ResizeEvent
]


# Pattern to match VTNext input events
EVENT_PATTERN = re.compile(r"\x1b\]vtni;([^;]+);([^\x07]*)\x07")


def parse_event(data: str) -> Optional[InputEvent]:
    """Parse a VTNext input event from a string."""
    match = EVENT_PATTERN.search(data)
    if not match:
        return None

    event_type = match.group(1)
    params = match.group(2).split(";")

    try:
        if event_type == "kd":  # key down
            return KeyDownEvent(
                keycode=int(params[0]),
                scancode=int(params[1]),
                modifiers=Modifiers(int(params[2])),
                timestamp=int(params[3]),
            )
        elif event_type == "ku":  # key up
            return KeyUpEvent(
                keycode=int(params[0]),
                scancode=int(params[1]),
                modifiers=Modifiers(int(params[2])),
                timestamp=int(params[3]),
            )
        elif event_type == "kr":  # key repeat
            return KeyRepeatEvent(
                keycode=int(params[0]),
                scancode=int(params[1]),
                modifiers=Modifiers(int(params[2])),
                timestamp=int(params[3]),
            )
        elif event_type == "kc":  # key char
            return KeyCharEvent(
                codepoint=int(params[0]),
                modifiers=Modifiers(int(params[1])),
                timestamp=int(params[2]),
            )
        elif event_type == "md":  # mouse down
            return MouseDownEvent(
                button=int(params[0]),
                x=float(params[1]),
                y=float(params[2]),
                modifiers=Modifiers(int(params[3])),
                timestamp=int(params[4]),
            )
        elif event_type == "mu":  # mouse up
            return MouseUpEvent(
                button=int(params[0]),
                x=float(params[1]),
                y=float(params[2]),
                modifiers=Modifiers(int(params[3])),
                timestamp=int(params[4]),
            )
        elif event_type == "mm":  # mouse move
            return MouseMoveEvent(
                x=float(params[0]),
                y=float(params[1]),
                dx=float(params[2]),
                dy=float(params[3]),
                modifiers=Modifiers(int(params[4])),
                timestamp=int(params[5]),
            )
        elif event_type == "mw":  # mouse wheel
            return ScrollEvent(
                dx=float(params[0]),
                dy=float(params[1]),
                x=float(params[2]),
                y=float(params[3]),
                modifiers=Modifiers(int(params[4])),
                timestamp=int(params[5]),
            )
        elif event_type == "focus":
            return FocusEvent(focused=params[0] == "1")
        elif event_type == "resize":
            return ResizeEvent(
                width=float(params[0]),
                height=float(params[1]),
            )
    except (IndexError, ValueError) as e:
        return None

    return None


class EventParser:
    """Streaming parser for VTNext input events."""

    def __init__(self):
        self.buffer = ""

    def feed(self, data: str) -> list[InputEvent]:
        """Feed data and return any complete events."""
        self.buffer += data
        events = []

        while True:
            match = EVENT_PATTERN.search(self.buffer)
            if not match:
                break

            event = parse_event(self.buffer[match.start():match.end()])
            if event:
                events.append(event)

            self.buffer = self.buffer[match.end():]

        # Prevent buffer from growing too large
        if len(self.buffer) > 10000:
            self.buffer = self.buffer[-1000:]

        return events
