"""
VTNext output commands - escape sequences to send to the terminal.
"""

import base64
from typing import Optional, Tuple, List

ESC = "\x1b"
BEL = "\x07"
PREFIX = f"{ESC}]vtn;"


def text(
    content: str,
    x: float = 0,
    y: float = 0,
    z: float = 0,
    rotation: float = 0,
    scale: float = 1.0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
) -> str:
    """Draw text at arbitrary position with optional rotation and scale."""
    r, g, b, a = color
    safe_content = content.replace('"', '\\"')
    return f'{PREFIX}text;{x};{y};{z};{rotation};{scale};{r};{g};{b};{a};"{safe_content}"{BEL}'


def char(
    codepoint: int,
    x: float = 0,
    y: float = 0,
    z: float = 0,
    rotation: float = 0,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
) -> str:
    """Draw a single character (by codepoint) with full transform control."""
    r, g, b, a = color
    return f"{PREFIX}char;{x};{y};{z};{rotation};{scale_x};{scale_y};{r};{g};{b};{a};{codepoint}{BEL}"


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    z: float = 0,
    rotation: float = 0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    filled: bool = True,
) -> str:
    """Draw a rectangle."""
    r, g, b, a = color
    f = 1 if filled else 0
    return f"{PREFIX}rect;{x};{y};{z};{width};{height};{rotation};{r};{g};{b};{a};{f}{BEL}"


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    z: float = 0,
    thickness: float = 1.0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
) -> str:
    """Draw a line."""
    r, g, b, a = color
    return f"{PREFIX}line;{x1};{y1};{x2};{y2};{z};{thickness};{r};{g};{b};{a}{BEL}"


def circle(
    cx: float,
    cy: float,
    radius: float,
    z: float = 0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    filled: bool = True,
) -> str:
    """Draw a circle."""
    r, g, b, a = color
    f = 1 if filled else 0
    return f"{PREFIX}circle;{cx};{cy};{z};{radius};{r};{g};{b};{a};{f}{BEL}"


def ellipse(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    z: float = 0,
    rotation: float = 0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    filled: bool = True,
) -> str:
    """Draw an ellipse."""
    r, g, b, a = color
    f = 1 if filled else 0
    return f"{PREFIX}ellipse;{cx};{cy};{z};{rx};{ry};{rotation};{r};{g};{b};{a};{f}{BEL}"


def arc(
    cx: float,
    cy: float,
    radius: float,
    start_angle: float,
    end_angle: float,
    z: float = 0,
    thickness: float = 2.0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
) -> str:
    """Draw an arc."""
    r, g, b, a = color
    return f"{PREFIX}arc;{cx};{cy};{z};{radius};{start_angle};{end_angle};{thickness};{r};{g};{b};{a}{BEL}"


def polygon(
    points: List[Tuple[float, float]],
    z: float = 0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    filled: bool = True,
) -> str:
    """Draw a polygon from a list of (x, y) points."""
    r, g, b, a = color
    f = 1 if filled else 0
    n = len(points)
    pts_str = ";".join(f"{p[0]};{p[1]}" for p in points)
    return f"{PREFIX}poly;{z};{r};{g};{b};{a};{f};{n};{pts_str}{BEL}"


def rounded_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    z: float = 0,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    filled: bool = True,
) -> str:
    """Draw a rounded rectangle."""
    r, g, b, a = color
    f = 1 if filled else 0
    return f"{PREFIX}rrect;{x};{y};{z};{width};{height};{radius};{r};{g};{b};{a};{f}{BEL}"


def clear(
    color: Tuple[int, int, int, int] = (0, 0, 0, 255),
    region: Optional[Tuple[float, float, float, float]] = None,
) -> str:
    """Clear the viewport or a region."""
    r, g, b, a = color
    if region:
        rx, ry, rw, rh = region
        return f"{PREFIX}clear;{rx};{ry};{rw};{rh};{r};{g};{b};{a}{BEL}"
    return f"{PREFIX}clear;{r};{g};{b};{a}{BEL}"


def viewport(width: float, height: float) -> str:
    """Set the logical viewport size."""
    return f"{PREFIX}viewport;{width};{height}{BEL}"


def image(
    data: bytes,
    x: float = 0,
    y: float = 0,
    z: float = 0,
    width: float = 0,
    height: float = 0,
    rotation: float = 0,
    format: str = "png",
) -> str:
    """Draw an image."""
    b64 = base64.b64encode(data).decode("ascii")
    return f"{PREFIX}img;{x};{y};{z};{width};{height};{rotation};{format};{b64}{BEL}"


def layer_push(
    layer_id: str,
    x: float = 0,
    y: float = 0,
    width: float = 0,
    height: float = 0,
    opacity: float = 1.0,
) -> str:
    """Push a new layer."""
    return f"{PREFIX}layer;push;{layer_id};{x};{y};{width};{height};{opacity}{BEL}"


def layer_pop(layer_id: str) -> str:
    """Pop a layer."""
    return f"{PREFIX}layer;pop;{layer_id}{BEL}"


def query_version() -> str:
    """Query terminal version."""
    return f"{PREFIX}query;version{BEL}"


def query_size() -> str:
    """Query viewport size."""
    return f"{PREFIX}query;size{BEL}"


def query_features() -> str:
    """Query supported features."""
    return f"{PREFIX}query;features{BEL}"


def input_raw() -> str:
    """Enable raw input mode (game-engine style)."""
    return f"{PREFIX}input;raw{BEL}"


def input_normal() -> str:
    """Enable normal input mode (traditional terminal)."""
    return f"{PREFIX}input;normal{BEL}"


def cursor_hide() -> str:
    """Hide the cursor."""
    return f"{PREFIX}cursor;hide{BEL}"


def cursor_show() -> str:
    """Show the cursor."""
    return f"{PREFIX}cursor;show{BEL}"
