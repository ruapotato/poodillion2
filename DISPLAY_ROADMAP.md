# BrainhairOS Display Server Roadmap
## From Framebuffer to X11/Wayland-like System

**Vision**: A minimal, fast display server that's simpler than X11 but more capable than a basic framebuffer.

**Philosophy**: Start simple, architect for growth, maintain BrainhairOS principles (minimal, syscalls-only, composable).

---

## 🎯 Target Architecture (End Goal)

```
┌─────────────────────────────────────────────────────────┐
│                    Applications                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  gedit   │  │  browser │  │ terminal │    (Clients) │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼────────────────────┘
        │             │             │
   ┌────▼─────────────▼─────────────▼────┐
   │     PoodDisplay Protocol (PDP)      │  (Like X11 protocol but simpler)
   │  - Window operations                │
   │  - Drawing commands                 │
   │  - Input events                     │
   │  - IPC via Unix sockets or pipes    │
   └────────────────┬────────────────────┘
                    │
   ┌────────────────▼────────────────────┐
   │     poodd (Display Server)          │  (Like Xorg/Wayland compositor)
   │  ┌──────────────────────────────┐   │
   │  │  Compositor                  │   │
   │  │  - Manages windows           │   │
   │  │  - Renders to framebuffer    │   │
   │  │  - Handles input events      │   │
   │  └──────────────────────────────┘   │
   └────────────────┬────────────────────┘
                    │
   ┌────────────────▼────────────────────┐
   │         Hardware Layer               │
   │  - /dev/fb0 (framebuffer)           │
   │  - /dev/input/* (keyboard/mouse)    │
   │  - DRM/KMS (future: GPU accel)      │
   └─────────────────────────────────────┘
```

---

## 📅 Phase-by-Phase Evolution

### Phase 1: Foundation (Month 1-2) 🟢 START HERE
**Goal**: Get pixels on screen, basic drawing

**Deliverables**:
```bash
./bin/fbinit          # Initialize framebuffer
./bin/pixel x y rgb   # Plot a pixel
./bin/rect x y w h c  # Draw rectangle
./bin/line x1 y1 x2 y2 c  # Draw line
./bin/clear color     # Clear screen
```

**Architecture**: Direct framebuffer access, no abstractions yet

**Code**: ~500 lines total
- `lib/framebuffer.nim` - Core FB library
- `userland/fb*.nim` - Simple drawing utilities

**Key syscalls**:
```nim
const SYS_mmap: int32 = 90
const SYS_ioctl: int32 = 54
# Framebuffer ioctls
const FBIOGET_VSCREENINFO: int32 = 0x4600
const FBIOGET_FSCREENINFO: int32 = 0x4602
```

---

### Phase 2: Graphics Primitives (Month 2-3) 🟡
**Goal**: Complete 2D drawing library

**Deliverables**:
```bash
./bin/circle x y r c      # Circle
./bin/fill x y w h c      # Filled rectangle
./bin/blit src dest       # Copy image region
./bin/text x y "string"   # Render text
```

**New features**:
- Bitmap font rendering (8x8 or 8x16 fonts)
- Double buffering (eliminate flicker)
- Clipping regions
- Basic image format support (BMP or custom)

**Code**: +1000 lines
- Font data embedded in executable
- Back buffer allocation
- Optimized memcpy for blitting

---

### Phase 3: Input & Events (Month 3-4) 🟡
**Goal**: Mouse and keyboard input, event loop

**Deliverables**:
```bash
./bin/poodd-input     # Input daemon (reads /dev/input/*)
./bin/mouse-demo      # Shows mouse cursor
./bin/kbd-demo        # Keyboard events
```

**Architecture** (First abstraction!):
```
┌─────────────────┐
│   poodd-input   │  (Input server - runs in background)
│  - Reads /dev/input/mice, /dev/input/event*
│  - Broadcasts events via FIFO or pipe
└────────┬────────┘
         │ (events)
    ┌────▼────┐
    │  Apps   │
    └─────────┘
```

**Event format** (simple binary struct):
```nim
type InputEvent = object
  event_type: uint8   # 0=mouse, 1=keyboard
  x: int16            # mouse x or key code
  y: int16            # mouse y or modifier keys
  button: uint8       # button state or key press/release
  timestamp: uint32
```

**Code**: +800 lines
- Input daemon
- Event queue management
- Mouse cursor rendering

---

### Phase 4: Protocol Design (Month 4-5) 🟠 CRITICAL PHASE
**Goal**: Define PoodDisplay Protocol (PDP) - the foundation for client/server

**This is where we architect for X11/Wayland-like behavior!**

#### Protocol Design Principles:
1. **Simpler than X11** - No complex legacy cruft
2. **More structured than Wayland** - Not too free-form
3. **Binary protocol** - Fast, matches BrainhairOS data philosophy
4. **Stateless where possible** - Easier to debug/implement
5. **Extensible** - Can add features later

#### PoodDisplay Protocol (PDP) Specification:

**Transport**: Unix domain sockets (`/tmp/poodd.sock`)

**Message format**:
```nim
# All messages start with header
type PDPHeader = object
  msg_type: uint16      # Message type
  msg_length: uint16    # Total message length
  client_id: uint32     # Client identifier
  sequence: uint32      # Sequence number

# Message types
const PDP_CREATE_WINDOW: uint16 = 1
const PDP_DESTROY_WINDOW: uint16 = 2
const PDP_DRAW_RECT: uint16 = 3
const PDP_DRAW_TEXT: uint16 = 4
const PDP_BLIT_IMAGE: uint16 = 5
const PDP_SET_TITLE: uint16 = 6
const PDP_INPUT_EVENT: uint16 = 100  # Server -> Client
const PDP_EXPOSE_EVENT: uint16 = 101 # Server -> Client
```

**Example messages**:
```nim
# Create window
type PDPCreateWindow = object
  header: PDPHeader
  x: int16
  y: int16
  width: uint16
  height: uint16
  flags: uint32

# Draw rectangle
type PDPDrawRect = object
  header: PDPHeader
  window_id: uint32
  x: int16
  y: int16
  width: uint16
  height: uint16
  color: uint32

# Input event (server -> client)
type PDPInputEvent = object
  header: PDPHeader
  event_type: uint8   # mouse/keyboard
  x: int16
  y: int16
  button: uint8
  modifiers: uint8
```

**Deliverables**:
```bash
# Protocol specification
docs/PDP_SPEC.md

# Reference implementation
lib/pdp.nim           # Client library
lib/pdp_server.nim    # Server library

# Test utilities
./bin/pdp-send        # Send raw protocol messages
./bin/pdp-dump        # Debug protocol traffic
```

**Code**: +1500 lines
- Protocol implementation
- Socket handling
- Message serialization/deserialization

---

### Phase 5: Display Server (Month 5-7) 🔴 BIG STEP
**Goal**: First working client/server display system

**Architecture**:
```
┌─────────────────────────────────────┐
│         poodd (Display Server)      │
│                                     │
│  ┌────────────────────────────┐    │
│  │  Window Manager            │    │
│  │  - Window list             │    │
│  │  - Z-order (stacking)      │    │
│  │  - Focus tracking          │    │
│  └────────────────────────────┘    │
│                                     │
│  ┌────────────────────────────┐    │
│  │  Compositor                │    │
│  │  - Renders windows         │    │
│  │  - Decorations (borders)   │    │
│  │  - Damage tracking         │    │
│  └────────────────────────────┘    │
│                                     │
│  ┌────────────────────────────┐    │
│  │  Protocol Handler          │    │
│  │  - Socket server           │    │
│  │  - Client connections      │    │
│  │  - Message dispatch        │    │
│  └────────────────────────────┘    │
└─────────────────────────────────────┘
         ↑
    [Unix Socket]
         ↓
┌─────────────────┐
│  Client App     │
│  uses libpdp    │
└─────────────────┘
```

**Deliverables**:
```bash
# Display server (runs as daemon)
./bin/poodd

# Client library for apps
lib/libpdp.nim

# First graphical app!
./bin/hello-gui       # "Hello World" in a window

# Window manager tools
./bin/pdp-list        # List all windows
./bin/pdp-focus       # Focus a window
./bin/pdp-close       # Close a window
```

**Window representation**:
```nim
type Window = object
  id: uint32
  client_id: uint32
  x: int16
  y: int16
  width: uint16
  height: uint16
  title: array[64, uint8]
  buffer: ptr uint32      # Window's pixel buffer
  visible: bool
  focused: bool
  needs_redraw: bool
```

**Code**: +3000 lines
- Display server main loop
- Window management
- Compositing logic
- Client library

---

### Phase 6: Practical Desktop (Month 7-9) 🟠
**Goal**: Usable GUI environment with essential apps

**Deliverables**:
```bash
# Window manager with decorations
./bin/poodwm          # Title bars, borders, close buttons

# Essential apps
./bin/gterm           # Graphical terminal
./bin/gedit           # Graphical text editor
./bin/gfiles          # File manager
./bin/gcalc           # Calculator
./bin/gsysmon         # System monitor with graphs

# Desktop environment
./bin/pood-desktop    # Desktop with taskbar, launcher
```

**Features**:
- Window decorations (title bar, borders, buttons)
- Drag windows to move
- Resize windows
- Alt+Tab window switching
- Right-click context menus
- System tray
- Desktop wallpaper
- Application launcher

**Code**: +4000 lines
- Widget toolkit
- Desktop manager
- Application suite

---

### Phase 7: Advanced Features (Month 9-12) 🔴
**Goal**: Feature parity with basic X11/Wayland

**Deliverables**:
```bash
# Advanced compositor
./bin/poodd-comp      # Compositing with effects
# - Transparency/alpha blending
# - Shadows
# - Smooth animations
# - Multiple monitors

# Remote display
./bin/poodd-remote    # Display forwarding (like X11 over SSH)

# OpenGL/Vulkan support
./bin/poodd-accel     # Hardware acceleration

# Clipboard/drag-and-drop
# Copy/paste between apps
# Drag files between windows
```

**New protocols**:
```nim
# Extension messages
const PDP_SET_ALPHA: uint16 = 200
const PDP_CREATE_GL_CONTEXT: uint16 = 300
const PDP_CLIPBOARD_COPY: uint16 = 400
```

**Code**: +5000 lines

---

## 🏗️ Key Architectural Decisions

### 1. Protocol: Binary, not text (unlike X11)
**Why**: Faster, fits BrainhairOS data-oriented philosophy
```nim
# X11 uses text protocol:
"CreateWindow 640x480+100+100"

# PDP uses binary structs:
struct { type: 1, w: 640, h: 480, x: 100, y: 100 }
```

### 2. Compositing: Built-in from day 1 (like Wayland)
**Why**: Modern expectation, easier to add early than retrofit
```nim
# Every window has its own buffer
# Server composites them to framebuffer
```

### 3. IPC: Unix sockets (like both X11 and Wayland)
**Why**:
- Standard, works well
- Can do network transparency later (like X11)
- Or keep local-only (like Wayland)

### 4. State: Server-side window state (like X11)
**Why**: Simpler for clients, easier to implement window manager
```nim
# Server tracks:
- Window position, size
- Z-order
- Visibility
- Focus

# Clients just send draw commands
```

### 5. Rendering: Server-side for Phase 1-6
**Client-side option in Phase 7** (shared memory buffers)
```nim
# Phase 1-6: Client sends draw commands
client -> server: "draw_rect(10, 10, 100, 50, red)"

# Phase 7: Client draws to shared buffer
client: writes pixels to shared_mem
client -> server: "damage_region(10, 10, 100, 50)"
```

---

## 📊 Comparison with X11/Wayland

| Feature | X11 | Wayland | BrainhairOS |
|---------|-----|---------|--------------|
| **Protocol** | Text | Binary | **Binary** ✓ |
| **Network** | Yes | No | **Optional** (Phase 7) |
| **Compositing** | External | Built-in | **Built-in** ✓ |
| **Window Mgmt** | Server-side | Client-side | **Server-side** |
| **Extensions** | Many | Some | **Minimal** (add as needed) |
| **Complexity** | Very High | Medium | **Low** ✓ |
| **Size** | ~5MB | ~500KB | **~100KB** (target) ✓ |

---

## 🎯 Success Metrics

### Phase 1 (Month 2):
- ✅ Can draw pixels to screen
- ✅ Basic shapes working
- ✅ Framebuffer library < 5KB

### Phase 3 (Month 4):
- ✅ Mouse cursor visible and responsive
- ✅ Keyboard input working
- ✅ Can build interactive demos

### Phase 5 (Month 7):
- ✅ Client/server architecture working
- ✅ Can run multiple windows
- ✅ At least one graphical app runs
- ✅ Total code < 50KB

### Phase 6 (Month 9):
- ✅ Usable desktop environment
- ✅ Can do real work (edit files, browse files)
- ✅ Window management feels natural

### Phase 7 (Month 12):
- ✅ Feature-complete display server
- ✅ Performance comparable to X11/Wayland
- ✅ Can run complex graphical apps
- ✅ Total code < 150KB

---

## 🚀 Getting Started (Next Steps)

### Week 1-2: Framebuffer Foundation
```bash
# Create these files:
lib/framebuffer.nim           # Core FB library
userland/fbinit.nim          # Initialize FB
userland/pixel.nim           # Plot pixels
userland/clear.nim           # Clear screen
userland/demo.nim            # Draw some shapes

# Goal: See colored pixels on screen!
```

### Week 3-4: Graphics Primitives
```bash
# Add to lib/framebuffer.nim:
proc draw_rect()
proc draw_line()
proc draw_circle()
proc fill_rect()

# Create utilities:
userland/rect.nim
userland/line.nim
userland/circle.nim
```

### Month 2: Text Rendering
```bash
# Embed a bitmap font
lib/font_8x8.nim

# Add text rendering
proc draw_char()
proc draw_string()

# Create utility:
userland/text.nim
```

---

## 💡 Why This Will Work for BrainhairOS

1. **Incremental**: Each phase delivers working software
2. **Minimal**: No bloat, no unnecessary features
3. **Composable**: Small utilities that work together
4. **Educational**: Learn display servers from scratch
5. **Fast**: Binary protocol, direct framebuffer access
6. **Small**: Target < 150KB for entire stack
7. **Philosophy-aligned**: Data-oriented, syscalls-only

**The beauty**: You can stop at ANY phase and have something useful!
- Phase 2: Graphical demos and animations
- Phase 3: Interactive graphical programs
- Phase 5: Basic window system
- Phase 6: Full desktop environment
- Phase 7: Modern display server

---

## 🎨 Example: Simple Window App (Phase 5)

```nim
# hello-gui.nim - First graphical application

# Link against libpdp.nim
extern proc pdp_connect(): int32
extern proc pdp_create_window(x: int16, y: int16, w: uint16, h: uint16): uint32
extern proc pdp_draw_rect(win_id: uint32, x: int16, y: int16, w: uint16, h: uint16, color: uint32)
extern proc pdp_draw_text(win_id: uint32, x: int16, y: int16, text: ptr uint8)
extern proc pdp_poll_event(): InputEvent

proc main() =
  # Connect to display server
  discard pdp_connect()

  # Create window
  var win: uint32 = pdp_create_window(100, 100, 400, 300)

  # Draw background
  pdp_draw_rect(win, 0, 0, 400, 300, 0xFFFFFF)

  # Draw text
  pdp_draw_text(win, 150, 140, cast[ptr uint8]("Hello, BrainhairOS!"))

  # Event loop
  var running: int32 = 1
  while running != 0:
    var event: InputEvent = pdp_poll_event()
    if event.event_type == 1:  # keyboard
      if event.x == 27:  # ESC key
        running = 0

  discard syscall1(SYS_exit, 0)
```

**Compile**:
```bash
make bin/hello-gui
```

**Run**:
```bash
# Start display server
./bin/poodd &

# Run app
./bin/hello-gui
```

**Output**: A white window with "Hello, BrainhairOS!" centered!

---

Want me to start building Phase 1 (Framebuffer Foundation) right now?
I can create the initial framebuffer library and a few demo utilities to get you started!
