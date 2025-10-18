# PoodillionOS Windowing System Design

**Goal**: Build a modern display server from scratch - simpler than X11, more integrated than Wayland, perfectly suited for PoodillionOS's data-oriented philosophy.

---

## 🎯 Design Principles

### 1. **Data-Oriented**
- Windows, events, drawing commands are all structured binary data
- Use PSCH schema format for everything
- Zero-copy where possible

### 2. **Simpler than X11**
- No 40-year legacy cruft
- No Xlib complexity
- Clean, minimal protocol
- ~20-30 message types vs X11's 100+

### 3. **More Integrated than Wayland**
- Not just a protocol - full stack
- Built-in compositor
- Native text rendering
- Integrated with PoodillionOS data streams

### 4. **Modern Choices**
- Binary protocol (not X11's wire format complexity)
- Direct framebuffer + DRM/KMS (no legacy VGA)
- Compositing built-in (not bolted on like X11)
- Security by design (not an afterthought)

---

## 🏗️ Architecture

### Three-Layer Stack

```
┌─────────────────────────────────────────┐
│  Applications                            │
│  - Terminal (xterm replacement)         │
│  - Editor (GUI version of edit)         │
│  - File Manager                          │
│  └─ Use: libpood (client library)       │
├─────────────────────────────────────────┤
│  Window Manager / Compositor             │
│  - poodwm: Tiling + floating            │
│  - Compositing effects                   │
│  - Window decorations                    │
│  └─ Talks to: poodd via sockets         │
├─────────────────────────────────────────┤
│  Display Server                          │
│  - poodd: Core display daemon            │
│  - Framebuffer management                │
│  - Input handling (mouse, keyboard)      │
│  - Protocol: PoodDisplay Protocol (PDP)  │
│  └─ Direct: /dev/fb0, /dev/input/*      │
└─────────────────────────────────────────┘
```

---

## 📡 Protocol Design: PDP (PoodDisplay Protocol)

### Core Concepts

**Everything is binary structured data** - just like the rest of PoodillionOS!

### Message Format (PSCH-based)

```
Header (8 bytes):
  Magic: "PPDP" (4 bytes)
  Version: 1 (1 byte)
  Message Type: uint8
  Message Length: uint16

Payload (variable):
  Binary data specific to message type
```

### Message Types (~25 total)

#### Window Operations (10 messages)
```nim
type WindowCreate = object
  width: uint16
  height: uint16
  x: int16
  y: int16
  flags: uint32  # RESIZABLE, DECORATED, FULLSCREEN, etc

type WindowDestroy = object
  window_id: uint32

type WindowMove = object
  window_id: uint32
  x: int16
  y: int16

type WindowResize = object
  window_id: uint32
  width: uint16
  height: uint16

type WindowShow = object
  window_id: uint32

type WindowHide = object
  window_id: uint32

type WindowSetTitle = object
  window_id: uint32
  title: array[64, char]

type WindowRaise = object
  window_id: uint32

type WindowLower = object
  window_id: uint32

type WindowSetIcon = object
  window_id: uint32
  icon_data: ptr uint8  # Reference to shared memory
  width: uint16
  height: uint16
```

#### Drawing Commands (8 messages)
```nim
type DrawPixel = object
  window_id: uint32
  x: int16
  y: int16
  color: uint32

type DrawLine = object
  window_id: uint32
  x1: int16
  y1: int16
  x2: int16
  y2: int16
  color: uint32
  thickness: uint8

type DrawRect = object
  window_id: uint32
  x: int16
  y: int16
  width: uint16
  height: uint16
  color: uint32
  filled: bool

type DrawText = object
  window_id: uint32
  x: int16
  y: int16
  text: array[256, char]
  color: uint32
  font_id: uint16

type DrawBitmap = object
  window_id: uint32
  x: int16
  y: int16
  width: uint16
  height: uint16
  bitmap_id: uint32  # Reference to shared bitmap

type ClearWindow = object
  window_id: uint32
  color: uint32

type SwapBuffers = object
  window_id: uint32

type CreateBitmap = object
  width: uint16
  height: uint16
  # Returns: bitmap_id
```

#### Input Events (4 messages)
```nim
type MouseMove = object
  window_id: uint32
  x: int16
  y: int16
  timestamp: uint64

type MouseButton = object
  window_id: uint32
  button: uint8  # LEFT=1, MIDDLE=2, RIGHT=3
  pressed: bool
  x: int16
  y: int16
  timestamp: uint64

type KeyPress = object
  window_id: uint32
  keycode: uint32
  pressed: bool
  modifiers: uint8  # SHIFT, CTRL, ALT, etc
  timestamp: uint64

type WindowFocus = object
  window_id: uint32
  focused: bool
```

#### System Messages (3 messages)
```nim
type Ping = object
  timestamp: uint64

type Pong = object
  timestamp: uint64

type Error = object
  error_code: uint32
  message: array[128, char]
```

---

## 🎨 Font Rendering

### Bitmap Fonts (Phase 1)

Start simple - embedded 8x16 bitmap fonts:

```nim
# 8x16 ASCII font (128 chars * 16 bytes = 2KB)
const FONT_8x16: array[128 * 16, uint8] = [
  # Character data
  # Each char is 8 pixels wide, 16 pixels tall
  # 1 byte per row (8 bits)
]

proc draw_char(fb: ptr uint32, x: int, y: int, c: char, color: uint32) =
  var char_offset = int(c) * 16
  for row in 0..15:
    var bits = FONT_8x16[char_offset + row]
    for col in 0..7:
      if (bits and (1 << col)) != 0:
        plot_pixel(fb, x + col, y + row, color)
```

### TrueType Support (Phase 2)

Later: stb_truetype.h style single-file TTF rasterizer

---

## 🖱️ Input System

### Mouse Input

```nim
# Read from /dev/input/mice (PS/2 protocol)
type MouseEvent = object
  buttons: uint8    # bit 0=left, 1=right, 2=middle
  dx: int8          # relative x movement
  dy: int8          # relative y movement

proc read_mouse_event(fd: int32): MouseEvent =
  var buf: array[3, uint8]
  discard syscall3(SYS_read, fd, cast[int32](addr(buf)), 3)

  result.buttons = buf[0] and 0x07
  result.dx = cast[int8](buf[1])
  result.dy = cast[int8](buf[2])
```

### Keyboard Input

```nim
# Read from /dev/input/eventX (evdev protocol)
type KeyEvent = object
  timestamp: uint64
  type: uint16      # EV_KEY
  code: uint16      # KEY_A, KEY_ESC, etc
  value: int32      # 0=release, 1=press, 2=repeat

proc read_key_event(fd: int32): KeyEvent =
  discard syscall3(SYS_read, fd, cast[int32](addr(result)), 24)
```

---

## 💻 Display Server: `poodd`

### Main Loop

```nim
proc main() =
  # Open framebuffer
  var fb_fd = open("/dev/fb0", O_RDWR)
  var fb = mmap(...)  # Or use lseek+write approach

  # Open input devices
  var mouse_fd = open("/dev/input/mice", O_RDONLY)
  var kbd_fd = open("/dev/input/event0", O_RDONLY)

  # Create Unix socket for clients
  var server_socket = create_unix_socket("/tmp/pood.socket")

  # Main event loop
  while true:
    # Poll for events (select/poll/epoll)
    var fds = [server_socket, mouse_fd, kbd_fd]
    var ready = poll(fds)

    if ready[server_socket]:
      # New client connection
      handle_new_client()

    if ready[mouse_fd]:
      # Mouse event
      var event = read_mouse_event(mouse_fd)
      dispatch_to_windows(event)

    if ready[kbd_fd]:
      # Keyboard event
      var event = read_key_event(kbd_fd)
      dispatch_to_focused_window(event)

    # Process client messages
    for client in clients:
      if has_data(client):
        var msg = read_message(client)
        handle_client_message(client, msg)

    # Composite and render
    composite_windows()
    swap_buffers()
```

### Window Management

```nim
type Window = object
  id: uint32
  x: int16
  y: int16
  width: uint16
  height: uint16
  title: array[64, char]
  buffer: ptr uint32  # Offscreen buffer
  visible: bool
  focused: bool
  client_socket: int32

var windows: seq[Window]
var next_window_id: uint32 = 1

proc create_window(width: uint16, height: uint16): uint32 =
  var win: Window
  win.id = next_window_id
  next_window_id += 1
  win.width = width
  win.height = height
  win.buffer = allocate_buffer(width, height)
  windows.add(win)
  return win.id
```

### Compositing

```nim
proc composite_windows() =
  # Clear framebuffer to background
  clear_screen(fb, BACKGROUND_COLOR)

  # Render windows back-to-front
  for win in windows:
    if win.visible:
      blit_window(win, fb)
      if win.focused:
        draw_window_border(win, FOCUSED_COLOR)
      else:
        draw_window_border(win, UNFOCUSED_COLOR)

  # Render mouse cursor on top
  draw_cursor(fb, mouse_x, mouse_y)
```

---

## 📚 Client Library: `libpood`

### C API (for compatibility)

```c
typedef struct PoodWindow PoodWindow;

// Connection
PoodDisplay* pood_connect(const char* socket_path);
void pood_disconnect(PoodDisplay* display);

// Window operations
PoodWindow* pood_create_window(PoodDisplay* d, int w, int h);
void pood_destroy_window(PoodWindow* win);
void pood_show_window(PoodWindow* win);
void pood_hide_window(PoodWindow* win);

// Drawing
void pood_clear(PoodWindow* win, uint32_t color);
void pood_draw_pixel(PoodWindow* win, int x, int y, uint32_t color);
void pood_draw_line(PoodWindow* win, int x1, int y1, int x2, int y2, uint32_t color);
void pood_draw_rect(PoodWindow* win, int x, int y, int w, int h, uint32_t color);
void pood_draw_text(PoodWindow* win, int x, int y, const char* text, uint32_t color);
void pood_swap_buffers(PoodWindow* win);

// Events
typedef struct {
    enum { MOUSE_MOVE, MOUSE_BUTTON, KEY_PRESS, WINDOW_CLOSE } type;
    union {
        struct { int x, y; } mouse_move;
        struct { int button; bool pressed; } mouse_button;
        struct { int keycode; bool pressed; } key;
    };
} PoodEvent;

bool pood_poll_event(PoodDisplay* d, PoodEvent* event);
```

### Mini-Nim API

```nim
type PoodDisplay = object
  socket_fd: int32

type PoodWindow = object
  display: ptr PoodDisplay
  window_id: uint32
  width: uint16
  height: uint16

proc connect(): PoodDisplay =
  var fd = socket(AF_UNIX, SOCK_STREAM, 0)
  # connect to /tmp/pood.socket
  result.socket_fd = fd

proc create_window(d: ptr PoodDisplay, w: uint16, h: uint16): PoodWindow =
  var msg: WindowCreate
  msg.width = w
  msg.height = h
  send_message(d.socket_fd, MSG_WINDOW_CREATE, addr(msg))
  var response = receive_message(d.socket_fd)
  result.window_id = response.window_id
  result.display = d
  result.width = w
  result.height = h

proc draw_pixel(w: ptr PoodWindow, x: int16, y: int16, color: uint32) =
  var msg: DrawPixel
  msg.window_id = w.window_id
  msg.x = x
  msg.y = y
  msg.color = color
  send_message(w.display.socket_fd, MSG_DRAW_PIXEL, addr(msg))
```

---

## 🎮 Example Applications

### 1. Simple Window

```nim
# hello_window.nim
var display = connect()
var window = create_window(addr(display), 640, 480)

# Clear to blue
clear_window(addr(window), 0x0000FF)

# Draw white text
draw_text(addr(window), 10, 10, "Hello, PoodillionOS!", 0xFFFFFF)

# Show window
show_window(addr(window))
swap_buffers(addr(window))

# Event loop
while true:
  var event: PoodEvent
  if poll_event(addr(display), addr(event)):
    if event.type == KEY_PRESS and event.key.keycode == KEY_ESC:
      break

destroy_window(addr(window))
disconnect(addr(display))
```

### 2. Graphics Demo

```nim
# graphics_demo.nim
var display = connect()
var window = create_window(addr(display), 800, 600)
show_window(addr(window))

while true:
  # Animate some shapes
  clear_window(addr(window), 0x000000)

  # Draw moving circle
  var x = (frame_count % 800)
  draw_circle(addr(window), x, 300, 50, 0xFF0000)

  # Draw rotating line
  var angle = frame_count * 0.1
  draw_line(addr(window), 400, 300,
            400 + cos(angle) * 200,
            300 + sin(angle) * 200, 0x00FF00)

  swap_buffers(addr(window))
  frame_count += 1
```

### 3. Terminal Emulator

```nim
# poodterm.nim - Terminal emulator
var display = connect()
var window = create_window(addr(display), 800, 600)
show_window(addr(window))

var terminal_state: TerminalState
terminal_state.cursor_x = 0
terminal_state.cursor_y = 0
terminal_state.buffer = allocate_terminal_buffer(80, 25)

while true:
  var event: PoodEvent
  if poll_event(addr(display), addr(event)):
    if event.type == KEY_PRESS:
      handle_keypress(addr(terminal_state), event.key.keycode)

  render_terminal(addr(window), addr(terminal_state))
  swap_buffers(addr(window))
```

---

## 🚀 Implementation Roadmap

### Phase 1: Core Infrastructure (2-3 weeks)
- [ ] Unix socket server in `poodd`
- [ ] Message parsing (PDP protocol)
- [ ] Basic window creation/destruction
- [ ] Single window rendering

### Phase 2: Input (1-2 weeks)
- [ ] Mouse input (`/dev/input/mice`)
- [ ] Keyboard input (`/dev/input/event0`)
- [ ] Event dispatch to windows
- [ ] Focus management

### Phase 3: Font Rendering (1 week)
- [ ] Embed 8x16 bitmap font
- [ ] `draw_char()` function
- [ ] `draw_text()` with wrapping
- [ ] Cursor rendering

### Phase 4: Client Library (1-2 weeks)
- [ ] `libpood.nim` - Mini-Nim API
- [ ] `libpood.c` - C API (optional)
- [ ] Example applications
- [ ] Documentation

### Phase 5: Window Manager (2-3 weeks)
- [ ] Multiple window support
- [ ] Z-order management
- [ ] Window decorations
- [ ] Resize/move operations
- [ ] Tiling layout algorithm

### Phase 6: Compositing (1-2 weeks)
- [ ] Double buffering
- [ ] Damage tracking
- [ ] Alpha blending
- [ ] Simple animations

### Phase 7: Desktop Environment (3-4 weeks)
- [ ] Terminal emulator (`poodterm`)
- [ ] File manager
- [ ] Text editor (GUI version of `edit`)
- [ ] Launcher/taskbar
- [ ] Settings panel

---

## 🎯 What Makes This Different?

### vs X11
- **Simpler**: ~30 message types vs 100+
- **Modern**: Compositing built-in, not bolted on
- **Binary**: PSCH format, not X11 wire protocol
- **Integrated**: Part of OS, not separate layer

### vs Wayland
- **Complete**: Not just a protocol - full stack
- **Integrated**: Native text, fonts, rendering
- **Data-oriented**: Uses PoodillionOS binary streams
- **Simpler**: Built-in compositor, no separate weston

### vs Windows/macOS
- **Open**: GPL, hackable
- **Minimal**: ~20-30KB for core display server
- **Direct**: Framebuffer + DRM, no HAL bloat
- **Type-safe**: Mini-Nim compiled, no C pointer bugs

---

## 📊 Size Estimates

```
Component               Size      Lines
--------------------------------------
poodd (display server)  ~20KB     ~2000 LOC
libpood (client lib)    ~5KB      ~500 LOC
poodwm (window manager) ~15KB     ~1500 LOC
poodterm (terminal)     ~10KB     ~1000 LOC
--------------------------------------
Total Display System    ~50KB     ~5000 LOC
```

Compare:
- X.Org Server: ~2MB, 300K+ LOC
- Weston (Wayland): ~500KB, 50K+ LOC
- Windows DWM: ~several MB
- macOS WindowServer: ~several MB

**PoodillionOS windowing: 50KB total - 100x smaller!**

---

## 🎨 Next Steps

1. **Implement text rendering** (NEXT!)
   - Embed 8x16 bitmap font
   - Create `draw_char()` and `draw_text()`
   - Test with "Hello World" window

2. **Add mouse support**
   - Read `/dev/input/mice`
   - Track mouse position
   - Draw cursor
   - Dispatch mouse events

3. **Build `poodd` server**
   - Unix socket listener
   - Message parsing
   - Window management
   - Compositing loop

4. **Create `libpood` client library**
   - Connection management
   - Message encoding
   - Event polling
   - Drawing primitives

5. **Write first GUI app**
   - Simple window with text
   - Mouse click handler
   - Keyboard input
   - Prove the concept!

---

**Let's build this!** 🚀

The foundation is ready. Graphics primitives work. Time to build the display server!
