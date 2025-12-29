# VTNext Protocol Specification v0.1

A next-generation terminal protocol for rich 2D/3D rendering with game-engine style input.

## Overview

VTNext extends the VT100 escape sequence model to support:
- Pixel-precise positioning (floating point)
- Character rotation and scaling
- Z-depth layering
- Inline image rendering
- Game-engine style input events (key down/up, modifiers)

## Escape Sequence Format

All VTNext commands use the format:
```
ESC ] v t n ; <command> ; <params> BEL
```
- `ESC` = 0x1B
- `]` = OSC introducer
- `vtn` = VTNext identifier
- `;` = separator
- `BEL` = 0x07 (terminator)

Alternative terminator: `ESC \` (ST)

## Coordinate System

- Origin (0,0) is top-left of viewport
- X increases rightward (pixels)
- Y increases downward (pixels)
- Z increases toward viewer (depth/layer ordering)
- All coordinates are 32-bit floats

---

## Output Commands

### 1. Draw Text
Draw text at arbitrary position with optional transforms.

```
ESC ] vtn ; text ; x ; y ; z ; rot ; scale ; r ; g ; b ; a ; "content" BEL
```

| Param | Type | Description |
|-------|------|-------------|
| x | f32 | X position (pixels) |
| y | f32 | Y position (pixels) |
| z | f32 | Z depth (0 = back, higher = front) |
| rot | f32 | Rotation in degrees (clockwise) |
| scale | f32 | Scale factor (1.0 = normal) |
| r,g,b,a | u8 | Color (0-255 each) |
| content | string | Text to render (UTF-8) |

Example:
```
ESC ] vtn ; text ; 100.0 ; 200.0 ; 1.0 ; 45.0 ; 1.5 ; 255 ; 128 ; 0 ; 255 ; "Hello" BEL
```

### 2. Draw Character
Single character with full transform control.

```
ESC ] vtn ; char ; x ; y ; z ; rot ; sx ; sy ; r ; g ; b ; a ; codepoint BEL
```

| Param | Type | Description |
|-------|------|-------------|
| sx, sy | f32 | Scale X and Y independently |
| codepoint | u32 | Unicode codepoint |

### 3. Draw Image
Render an image at position.

```
ESC ] vtn ; img ; x ; y ; z ; w ; h ; rot ; format ; base64data BEL
```

| Param | Type | Description |
|-------|------|-------------|
| w, h | f32 | Width/height (pixels, 0 = native) |
| format | string | "png", "jpg", "rgba" |
| base64data | string | Base64 encoded image data |

### 4. Draw Rectangle
```
ESC ] vtn ; rect ; x ; y ; z ; w ; h ; rot ; r ; g ; b ; a ; filled BEL
```

| Param | Type | Description |
|-------|------|-------------|
| filled | u8 | 0 = outline, 1 = filled |

### 5. Draw Line
```
ESC ] vtn ; line ; x1 ; y1 ; x2 ; y2 ; z ; thickness ; r ; g ; b ; a BEL
```

### 6. Draw Circle
```
ESC ] vtn ; circle ; cx ; cy ; z ; radius ; r ; g ; b ; a ; filled BEL
```

| Param | Type | Description |
|-------|------|-------------|
| cx, cy | f32 | Center position |
| radius | f32 | Circle radius |
| filled | u8 | 0 = outline, 1 = filled |

### 7. Draw Ellipse
```
ESC ] vtn ; ellipse ; cx ; cy ; z ; rx ; ry ; rot ; r ; g ; b ; a ; filled BEL
```

| Param | Type | Description |
|-------|------|-------------|
| rx, ry | f32 | X and Y radii |
| rot | f32 | Rotation in degrees |

### 8. Draw Arc
```
ESC ] vtn ; arc ; cx ; cy ; z ; radius ; start ; end ; thickness ; r ; g ; b ; a BEL
```

| Param | Type | Description |
|-------|------|-------------|
| start, end | f32 | Start/end angles in degrees |
| thickness | f32 | Arc line thickness |

### 9. Draw Polygon
```
ESC ] vtn ; poly ; z ; r ; g ; b ; a ; filled ; n ; x1 ; y1 ; x2 ; y2 ; ... BEL
```

| Param | Type | Description |
|-------|------|-------------|
| n | u32 | Number of points |
| x1, y1, ... | f32 | Point coordinates |

### 10. Draw Rounded Rectangle
```
ESC ] vtn ; rrect ; x ; y ; z ; w ; h ; radius ; r ; g ; b ; a ; filled BEL
```

| Param | Type | Description |
|-------|------|-------------|
| radius | f32 | Corner radius |

### 11. Clear
Clear the viewport or a region.

```
ESC ] vtn ; clear ; r ; g ; b ; a BEL
ESC ] vtn ; clear ; x ; y ; w ; h ; r ; g ; b ; a BEL
```

### 7. Set Viewport
Define the logical viewport size (for coordinate mapping).

```
ESC ] vtn ; viewport ; width ; height BEL
```

### 8. Push/Pop Layer
Create isolated rendering layers.

```
ESC ] vtn ; layer ; push ; id ; x ; y ; w ; h ; opacity BEL
ESC ] vtn ; layer ; pop ; id BEL
```

---

## Input Events

Input events are sent FROM terminal TO application as escape sequences.

### Event Format
```
ESC ] vtni ; <event_type> ; <params> BEL
```

### Key Events
```
ESC ] vtni ; kd ; keycode ; scancode ; modifiers ; timestamp BEL   (key down)
ESC ] vtni ; ku ; keycode ; scancode ; modifiers ; timestamp BEL   (key up)
ESC ] vtni ; kr ; keycode ; scancode ; modifiers ; timestamp BEL   (key repeat)
ESC ] vtni ; kc ; codepoint ; modifiers ; timestamp BEL            (character input)
```

| Param | Type | Description |
|-------|------|-------------|
| keycode | u32 | Virtual key code (USB HID based) |
| scancode | u32 | Physical scan code |
| modifiers | u32 | Modifier bitmask |
| timestamp | u64 | Microseconds since session start |
| codepoint | u32 | Unicode codepoint (for text input) |

### Modifier Bitmask
```
SHIFT_L   = 0x0001
SHIFT_R   = 0x0002
CTRL_L    = 0x0004
CTRL_R    = 0x0008
ALT_L     = 0x0010
ALT_R     = 0x0020
META_L    = 0x0040  (Super/Windows/Cmd)
META_R    = 0x0080
CAPS_LOCK = 0x0100  (state, not edge)
NUM_LOCK  = 0x0200
```

### Mouse Events
```
ESC ] vtni ; md ; button ; x ; y ; modifiers ; timestamp BEL   (mouse down)
ESC ] vtni ; mu ; button ; x ; y ; modifiers ; timestamp BEL   (mouse up)
ESC ] vtni ; mm ; x ; y ; dx ; dy ; modifiers ; timestamp BEL  (mouse move)
ESC ] vtni ; mw ; dx ; dy ; x ; y ; modifiers ; timestamp BEL  (scroll/wheel)
```

| Param | Type | Description |
|-------|------|-------------|
| button | u8 | 0=left, 1=right, 2=middle, 3+=extra |
| x, y | f32 | Position in pixels |
| dx, dy | f32 | Delta movement or scroll amount |

### Focus Events
```
ESC ] vtni ; focus ; 1 BEL   (gained focus)
ESC ] vtni ; focus ; 0 BEL   (lost focus)
```

### Resize Events
```
ESC ] vtni ; resize ; width ; height BEL
```

---

## Legacy VT100 Compatibility

VTNext supports a legacy compatibility mode for standard VT100/ANSI applications.

### Enable Legacy Subwindow
Create a region that interprets standard VT100 sequences:

```
ESC ] vtn ; legacy ; create ; id ; x ; y ; cols ; rows ; font_size BEL
ESC ] vtn ; legacy ; destroy ; id BEL
ESC ] vtn ; legacy ; write ; id ; base64data BEL
ESC ] vtn ; legacy ; focus ; id BEL
```

Legacy subwindows:
- Render a traditional character grid
- Support standard ANSI colors and attributes
- Forward input as cooked terminal input when focused

---

## Capability Query

Applications can query terminal capabilities:

```
ESC ] vtn ; query ; version BEL
ESC ] vtn ; query ; size BEL
ESC ] vtn ; query ; features BEL
```

Response:
```
ESC ] vtnr ; version ; 0 ; 1 ; 0 BEL
ESC ] vtnr ; size ; 1920 ; 1080 BEL
ESC ] vtnr ; features ; text ; img ; legacy BEL
```

---

## Session Control

### Input Mode
```
ESC ] vtn ; input ; raw BEL      (game-engine style, all events)
ESC ] vtn ; input ; normal BEL   (filtered, like traditional terminal)
```

### Cursor
```
ESC ] vtn ; cursor ; hide BEL
ESC ] vtn ; cursor ; show BEL
ESC ] vtn ; cursor ; set ; base64_png ; hotspot_x ; hotspot_y BEL
```

---

## Example Session

```
→ ESC ] vtn ; query ; version BEL
← ESC ] vtnr ; version ; 0 ; 1 ; 0 BEL

→ ESC ] vtn ; input ; raw BEL
→ ESC ] vtn ; cursor ; hide BEL
→ ESC ] vtn ; clear ; 20 ; 20 ; 30 ; 255 BEL
→ ESC ] vtn ; text ; 100 ; 100 ; 1 ; 0 ; 2.0 ; 255 ; 255 ; 255 ; 255 ; "VTNext Demo" BEL
→ ESC ] vtn ; rect ; 50 ; 50 ; 0 ; 200 ; 100 ; 15 ; 255 ; 0 ; 0 ; 128 ; 1 BEL

← ESC ] vtni ; kd ; 65 ; 30 ; 0 ; 1234567 BEL   (A key pressed)
← ESC ] vtni ; mm ; 150.5 ; 200.3 ; 2.0 ; -1.0 ; 0 ; 1234890 BEL  (mouse moved)
```

---

## Future Extensions

Reserved for future versions:
- 3D primitives (meshes, transforms)
- Audio cues
- Clipboard integration
- Drag and drop
- Multi-window/tab management
