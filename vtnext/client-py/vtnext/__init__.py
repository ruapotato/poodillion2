"""
VTNext Python Client Library

A next-generation terminal protocol with arbitrary positioning,
rotation, and game-engine style input.
"""

from .client import VTNextClient
from .commands import (
    text, char, rect, line, clear, viewport,
    image, layer_push, layer_pop,
    query_version, query_size, query_features,
    input_raw, input_normal, cursor_hide, cursor_show,
)
from .events import (
    InputEvent, KeyDownEvent, KeyUpEvent, KeyRepeatEvent, KeyCharEvent,
    MouseDownEvent, MouseUpEvent, MouseMoveEvent, ScrollEvent,
    FocusEvent, ResizeEvent,
    parse_event,
)

__version__ = "0.1.0"
__all__ = [
    "VTNextClient",
    "text", "char", "rect", "line", "clear", "viewport",
    "image", "layer_push", "layer_pop",
    "query_version", "query_size", "query_features",
    "input_raw", "input_normal", "cursor_hide", "cursor_show",
    "InputEvent", "KeyDownEvent", "KeyUpEvent", "KeyRepeatEvent", "KeyCharEvent",
    "MouseDownEvent", "MouseUpEvent", "MouseMoveEvent", "ScrollEvent",
    "FocusEvent", "ResizeEvent",
    "parse_event",
]
