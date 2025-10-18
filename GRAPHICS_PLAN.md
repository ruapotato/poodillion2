# PoodillionOS Graphics Plan

## Phase 1: Framebuffer Access (Week 1-2)

### Goals
- Open `/dev/fb0` and mmap it
- Get screen resolution and pixel format
- Plot pixels directly

### New syscalls needed
```nim
const SYS_mmap: int32 = 90
const SYS_ioctl: int32 = 54  # Already have this!

# Framebuffer ioctls
const FBIOGET_VSCREENINFO: int32 = 0x4600
const FBIOGET_FSCREENINFO: int32 = 0x4602
```

### First utility: `pixel.nim`
```nim
# Draw colored pixels on screen
./bin/pixel 100 100 255 0 0  # Red pixel at (100,100)
```

---

## Phase 2: Graphics Primitives (Week 3-4)

### Goals
- Rectangle drawing
- Line drawing (Bresenham's algorithm)
- Circle drawing
- Fill operations

### Utilities
```nim
# Draw shapes
./bin/rect 10 10 100 50 0xFF0000    # Red rectangle
./bin/line 0 0 100 100 0x00FF00     # Green line
./bin/circle 50 50 25 0x0000FF      # Blue circle
```

---

## Phase 3: Text Rendering (Week 5-6)

### Goals
- Bitmap font support (8x8 or 8x16)
- Text rendering to framebuffer
- Cursor support

### Font data
```nim
# Embed a simple bitmap font
const FONT_8x8: array[128 * 8, uint8] = [
  # ASCII font data
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Space
  # ... etc
]
```

### Utility
```nim
./bin/drawtext 10 10 "Hello World!" 0xFFFFFF
```

---

## Phase 4: Mouse Support (Week 7-8)

### Goals
- Read mouse events from `/dev/input/mice` or PS/2
- Track cursor position
- Detect clicks

### Utility
```nim
./bin/mouse  # Shows mouse position and button state
```

---

## Phase 5: Simple GUI Toolkit (Week 9-12)

### Goals
- Widget library (buttons, labels, text boxes)
- Event loop
- Simple layout system

### Example app
```nim
# Simple graphical calculator
./bin/calc
```

---

## Phase 6: Window Manager (Month 4-6)

### Goals
- Multiple windows
- Window decorations (title bar, borders)
- Focus management
- Basic compositing

### Architecture
```
┌─────────────────────────────────────┐
│          poodwm (window manager)    │
│  - Manages framebuffer              │
│  - Reads from client FIFOs          │
│  - Composites windows               │
└─────────────────────────────────────┘
         ↑                    ↑
    [FIFO/Pipe]          [FIFO/Pipe]
         ↓                    ↓
    ┌─────────┐          ┌─────────┐
    │  App 1  │          │  App 2  │
    └─────────┘          └─────────┘
```

---

## Alternative: Simpler "Kiosk Mode" GUI

Instead of full window manager, do single-app fullscreen GUIs:

```nim
# File manager with GUI
./bin/files
# - Shows files in grid
# - Click to open
# - Graphical dialogs

# Text editor with GUI
./bin/gedit
# - Graphical menus
# - Syntax highlighting
# - Mouse selection

# System monitor
./bin/monitor
# - CPU/Memory graphs
# - Process list with GUI
```

---

## Technical Challenges

### 1. Framebuffer specifics
- Need to detect pixel format (RGB, BGR, etc.)
- Handle different bit depths (16-bit, 24-bit, 32-bit)
- Deal with stride/pitch

### 2. Double buffering
- Allocate second buffer with `brk` or `mmap`
- Render to back buffer
- Memcpy to framebuffer (avoid flicker)

### 3. Font rendering
- Could embed bitmap font in executable
- Or load from file (PSF format is simple)
- Or generate at compile-time

### 4. Performance
- Framebuffer writes can be slow
- Minimize redraws (damage tracking)
- Use `memcpy` for block operations

---

## Framebuffer Code Example

```nim
# fb.nim - Framebuffer library

const SYS_open: int32 = 5
const SYS_ioctl: int32 = 54
const SYS_mmap: int32 = 90
const SYS_close: int32 = 6

const O_RDWR: int32 = 2
const PROT_READ: int32 = 1
const PROT_WRITE: int32 = 2
const MAP_SHARED: int32 = 1

const FBIOGET_VSCREENINFO: int32 = 0x4600

# Variable screen info
type VScreenInfo = object
  xres: uint32
  yres: uint32
  xres_virtual: uint32
  yres_virtual: uint32
  bits_per_pixel: uint32
  # ... more fields

var fb_fd: int32
var fb_ptr: ptr uint32
var screen_width: int32
var screen_height: int32

proc init_framebuffer(): int32 =
  # Open framebuffer
  fb_fd = syscall2(SYS_open, cast[int32]("/dev/fb0"), O_RDWR)
  if fb_fd < 0:
    return -1

  # Get screen info
  var vinfo: VScreenInfo
  var result: int32 = syscall3(SYS_ioctl, fb_fd, FBIOGET_VSCREENINFO,
                               cast[int32](addr(vinfo)))
  if result < 0:
    return -1

  screen_width = cast[int32](vinfo.xres)
  screen_height = cast[int32](vinfo.yres)

  # Memory map framebuffer
  var screen_size: int32 = screen_width * screen_height * 4
  fb_ptr = cast[ptr uint32](
    syscall6(SYS_mmap, 0, screen_size,
             PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0)
  )

  return 0

proc plot_pixel(x: int32, y: int32, color: uint32) =
  if x >= 0:
    if x < screen_width:
      if y >= 0:
        if y < screen_height:
          var offset: int32 = y * screen_width + x
          fb_ptr[offset] = color

proc fill_rect(x: int32, y: int32, w: int32, h: int32, color: uint32) =
  var row: int32 = 0
  while row < h:
    var col: int32 = 0
    while col < w:
      plot_pixel(x + col, y + row, color)
      col = col + 1
    row = row + 1

proc clear_screen(color: uint32) =
  fill_rect(0, 0, screen_width, screen_height, color)
```

---

## Size Estimates

- **Framebuffer library**: ~1-2KB
- **Graphics primitives**: ~2-3KB
- **Font rendering**: ~2-3KB (+ font data ~1KB)
- **Mouse driver**: ~1-2KB
- **Simple GUI app**: ~5-10KB

**Total for basic GUI**: ~15-25KB of utilities!

---

## Next Steps

1. **Start simple**: Get framebuffer working, plot some pixels
2. **Build incrementally**: Add one primitive at a time
3. **Test constantly**: Visual feedback is immediate!
4. **Reuse existing code**: Your syscall library already has most of what you need

The beauty is that this fits perfectly with PoodillionOS philosophy:
- **Minimal**: Just framebuffer, no complex drivers
- **Syscalls only**: No libc needed
- **Small binaries**: Each utility does one thing
- **Composable**: Build complex UIs from simple tools
