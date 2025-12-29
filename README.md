# BrainhairOS

**A Data-Oriented Operating System with Type-Safe Binary Pipelines**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

*Unix Performance + PowerShell Composability + Type Safety = **BrainhairOS***

---

## 🎯 What Makes BrainhairOS Different?

Unlike Unix (text streams) or PowerShell (serialized objects), BrainhairOS uses **binary typed data structures** throughout the entire system.

### The Problem with Text Pipes

```bash
# Unix way - fragile, slow, error-prone
$ ps aux | grep python | awk '{print $2}' | xargs kill
# What if process name has spaces? What if columns shift?
```

### The PowerShell Approach

```powershell
# Better composability, but slow serialization
PS> Get-Process | Where-Object {$_.Name -eq "python"} | Stop-Process
# Nice, but .NET object serialization is expensive
```

### The BrainhairOS Way

```bash
# Type-safe, binary, zero-copy pipelines
$ ps | where .name == "python" | select .pid | kill
# Schema: Process{pid:i32, name:str, mem:u64}
# Data: Binary structs, no parsing, no serialization
```

## 🎨 The Type-Aware Shell

BrainhairOS includes `psh`, a **badass type-aware shell** that automatically detects and beautifully displays structured data!

```bash
$ ./bin/psh

╔════════════════════════════════════════════════╗
║  BrainhairOS Shell - Type-Aware Data Shell   ║
║                                                ║
║  • Type-safe binary pipelines                 ║
║  • Automatic schema detection                 ║
║  • Pretty table formatting                    ║
║                                                ║
║  Try: bin/ps | bin/where | bin/select         ║
╚════════════════════════════════════════════════╝

psh> bin/ps

┌─── Schema ───────────────────────┐
│ Magic:   PSCH                     │
│ Version: 1                        │
│ Fields:  3                        │
│ RecSize: 12 bytes                 │
└──────────────────────────────────┘

┌─── Data (3 records) ───────────────┐
│ [0] 01 00 00 00 00 04 00 00 00 00 00 00  │
│ [1] 64 00 00 00 00 08 00 00 00 00 00 00  │
│ [2] c8 00 00 00 00 10 00 00 00 00 00 00  │
└──────────────────────────────────┘
```

**No manual formatting needed** - the shell *understands* your data!

---

## 🚀 Current Status

### ✅ Working Now

**BrainhairOS Microkernel** (bare-metal x86):
- **Boots from BIOS** - Custom 2-stage bootloader
- **Protected mode** - Full 32-bit x86 with paging (16MB identity mapped)
- **Preemptive multitasking** - Timer-based scheduler, 64 process slots
- **IPC** - Synchronous message passing (send/recv/call/reply)
- **PS/2 keyboard** - IRQ-driven input with scancode translation
- **Serial console** - COM1 for headless operation
- **VGA text mode** - 80x25, 16 colors
- **Hierarchical filesystem** - ext2-like with inodes, directories, files
- **Virtual filesystems** - /proc, /sys, /dev with dynamic content
- **ELF loader** - Load and execute userspace programs
- **Networking** - E1000 NIC driver, ARP, IP, ICMP, UDP, DHCP, TCP protocols
- **HTTP Server** - Flask-style web framework with routing and handlers

**Microkernel Shell** (50+ built-in commands):
- **File ops**: ls, cat, cp, mv, rm, mkdir, touch, stat, size, df
- **Navigation**: cd, pwd
- **Text**: echo, wc, head, grep, xxd
- **System**: ps, uptime, date, mem, reboot, sysinfo
- **Network**: ping, ifconfig, arp
- **Fun**: banner, hello, guess, countdown, matrix, spin
- **Debug**: peek, poke, dump, fill, run, calc

**Shell Features**:
- **I/O redirection**: `echo hello > file`, `echo more >> file`
- **Pipes**: `ls | grep txt | wc`
- **Environment variables**: `export VAR=value`, `echo $VAR`
- **Command history**: Up/down arrows recall previous commands
- **Tab completion**: Commands and file paths
- **Variable expansion**: `$HOME`, `$PATH`, `$USER`

**Run the microkernel**:
```bash
make run-microkernel     # QEMU with VGA display
make run-microkernel-serial  # Headless via serial console
```

**Flask-Style Web Framework**:
```brainhair
import "lib/flask"

proc index(sock: int32, request: ptr uint8, path: ptr uint8) =
  text(sock, cast[ptr uint8]("Hello from BrainhairOS!"))

proc user_handler(sock: int32, request: ptr uint8, path: ptr uint8) =
  var id: ptr uint8 = get_route_param(cast[ptr uint8]("id"))
  text(sock, id)

proc search(sock: int32, request: ptr uint8, path: ptr uint8) =
  var q: ptr uint8 = get_query_param(cast[ptr uint8]("q"))
  if cast[int32](q) != 0:
    text(sock, q)

proc main(): int32 =
  discard route(cast[ptr uint8]("/"), cast[ptr uint8](index))
  discard get(cast[ptr uint8]("/users/:id"), cast[ptr uint8](user_handler))
  discard get(cast[ptr uint8]("/search"), cast[ptr uint8](search))
  return run(8080)
```

Features:
- **Route registration** - `route()`, `get()`, `post()`, `put()`, `delete()`, `any()`
- **Dynamic routes** - `/users/:id` with `get_route_param("id")`
- **Query strings** - `?q=hello&page=2` with `get_query_param("q")`
- **Request headers** - `get_header("Content-Type")`, `get_content_length()`
- **URL encoding** - `url_encode()`, `url_decode()`
- **Response helpers** - `html()`, `text()`, `json()`, `redirect()`, `not_found()`, `server_error()`
- **Full TCP stack** - SYN/ACK handshake, data transfer

**Userland Utilities** (all in Brainhair, no libc):
- **echo** (8.9KB) - Display text output
- **cat** (5.1KB) - Concatenate and display files
- **edit** (11KB) - CLI text editor with ANSI colors!
- **true** (4.8KB) - Exit with success code
- **false** (4.8KB) - Exit with failure code
- **webapp** (17KB) - Example Flask-style web application

**Type-Aware Shell** ⭐ NEW:
- **psh** (14KB) - BrainhairOS Shell with schema awareness!
  - Automatically detects PSCH format
  - Displays schemas in pretty boxes
  - Formats binary data as hex tables
  - Interactive REPL with psh> prompt

**Graphics Library** 🎨 NEW (direct framebuffer access!):
- **fbinfo** (9.6KB) - Display framebuffer information
- **clear** (9.3KB) - Clear screen to solid color
- **pixel** (9.0KB) - Draw individual pixels at x,y
- **line** (9.7KB) - Bresenham's line algorithm
- **rect** (9.3KB) - Draw filled rectangles
- **circle** (9.4KB) - Midpoint circle algorithm

**Key Innovation**: Direct write to `/dev/fb0` via lseek + write
- No mmap needed! (VTY console blocks mmap)
- Pure syscalls, no graphics libraries
- All shapes compile from Brainhair to x86

**VTNext Desktop Environment** 🖥️ NEW - Full Graphical Desktop!

BrainhairOS now includes a complete graphical desktop environment rendered over serial/TCP using the VTNext protocol. It's like X11 but simpler - apps send drawing commands that get rendered by a pygame-based terminal.

**Desktop Features:**
- **Draggable windows** - Click and drag titlebars to move windows
- **Window manager** - Dynamic window creation, close buttons, z-ordering
- **Taskbar** - App launcher buttons (Term, Demo, Pong)
- **Desktop icons** - Terminal, Files, Settings
- **Mouse + keyboard input** - Full event handling with keydown/keyup

**Built-in Apps:**
- **Demo** - Colorful graphics demo (rectangles, circles, lines, text)
- **Pong** - Classic game with AI opponent, smooth paddle controls
- **Terminal windows** - Open multiple terminal windows

**Run the Desktop:**
```bash
# Install pygame
pip install pygame

# Launch with helper script (recommended)
./tools/run_vtnext_tcp.sh

# Desktop starts automatically after boot
# Controls:
#   D - Launch Demo
#   P - Launch Pong (W/S or arrows to move, Q to quit)
#   T - Open Terminal window
#   Q - Quit desktop
#   Ctrl+Q - Close the terminal app
#   Mouse - Click buttons, drag windows by titlebar
```

**VTNext Protocol:**
- **Escape sequence based** - `\x1b]vtn;command;params\x07`
- **Rich primitives** - rect, circle, line, rounded rect, text
- **Double buffered** - `clear` draws to back buffer, `present` flips
- **Input events** - click, move, up, keydown, keyup
- **RGBA colors** - Full alpha channel support

**VTNext Commands:**
```
clear;r;g;b;a          - Clear back buffer with color
present                - Flip buffers to display frame
rect;x;y;z;w;h;...     - Draw rectangle (filled or outlined)
circle;x;y;z;r;...     - Draw circle
line;x1;y1;x2;y2;...   - Draw line
rrect;x;y;z;w;h;rad;.. - Rounded rectangle
text;x;y;z;font;scale;r;g;b;a;"string" - Draw text
cursor;show|hide       - Control cursor visibility
input;raw|cooked       - Set input mode
```

**Input Events (terminal → kernel):**
```
click;x;y;button       - Mouse button pressed
move;x;y               - Mouse moved (while dragging)
up;x;y;button          - Mouse button released
keydown;keycode        - Key pressed
keyup;keycode          - Key released
```

**Desktop Environment** 🖥️ (X11/Wayland alternative!):
- **bds** (24KB) - Brainhair Display Server
  - Integrated floating window manager
  - Taskbar with window buttons and launcher
  - Mouse-driven window management (drag, close, minimize)
  - Layered compositing with focus handling
- **term** (74KB) - Graphical Terminal Emulator
  - PTY-based (/dev/ptmx master/slave)
  - Fork/exec shell in child process
  - Full 8x8 bitmap font (A-Z, a-z, 0-9, symbols)
  - Non-blocking I/O for smooth operation
- **fm** (55KB) - Graphical File Manager
  - Directory browsing with folder/file icons
  - Mouse navigation and selection
  - Double-click to enter directories
  - Current path display
- **gedit** (65KB) - Graphical Text Editor
  - Full text editing (insert, delete, navigation)
  - File load/save with Ctrl+S
  - Arrow key cursor movement
  - Line-based scrolling for large files
  - Syntax-inspired dark color scheme

**Run on TTY** (not X11!):
```bash
# Switch to a TTY first (Ctrl+Alt+F3)
sudo ./bin/bds   # Full desktop environment
sudo ./bin/term  # Just the terminal
sudo ./bin/fm    # Just the file manager
sudo ./bin/gedit myfile.txt  # Just the editor
```

**Data-Oriented Tools** (working binary pipeline!):
- **ps** (10.7KB) - Read real `/proc` data, output binary Process objects
- **inspect** (9.6KB) - View schema and hex dump structured data
- **where** (10.8KB) - Filter by field: `where FIELD OP VALUE`
- **count** (9.4KB) - Count records in stream
- **head** (9.6KB) - Take first N records: `head N`
- **tail** (9.2KB) - Take last N records
- **select** (9.0KB) - Project specific fields
- **sort** (10.3KB) - Sort by field: `sort FIELD [desc]`
- **fmt** (10.4KB) - Format binary records as human-readable text
- **ls** (9.6KB) - List directory contents as structured data

**Shell Features** (psh - 19KB):
- 🎨 Beautiful box-drawing UI
- 🔍 Automatic PSCH format detection
- 📊 Pretty hex table formatting
- ⚡ Zero-copy data display
- 💻 Interactive REPL
- 🚀 **Full pipeline support**: `ps | sort 3 desc | head 10 | fmt`
- 📝 Command argument passing to child processes
- 🔧 Built-in commands: exit, quit

**Compiler Features**:
- Type-safe Brainhair → x86 compiler
- Block-scoped parsing with indentation
- Size-aware loads/stores (byte, word, dword)
- Address-of operator (`addr`) for safe pointer operations
- Logical operators: `and`, `or` with short-circuit evaluation
- Conditional expressions: `if cond: a else: b`
- Control flow: `break`, `continue` statements
- Unary operators: `-x`, `not x`
- **argc/argv support**: `get_argc()`, `get_argv(i)` builtins
- Dynamic stack allocation
- 45+ Linux syscalls exposed
- Zero dependencies (no libc!)

### 📊 Comparison

| Feature | Unix | PowerShell | **BrainhairOS** |
|---------|------|------------|------------------|
| Pipeline Data | Text | .NET Objects | **Binary Structs** |
| Performance | ⚡ Fast I/O | 🐢 Slow (serialize) | **⚡⚡ Zero-copy** |
| Type Safety | ❌ None | ⚠️ Runtime | **✅ Compile-time** |
| Composability | ⚠️ Text processing | ✅ Object methods | **✅ Type-safe operators** |
| Introspection | ❌ Manual | ✅ Reflection | **✅ Schema inspection** |
| Memory | ✅ Efficient | ❌ GC overhead | **✅ Stack/mmap only** |
| Shell UI | Plain text | Tables | **🎨 Beautiful box-drawing** |
| Auto-formatting | ❌ None | ✅ Format-Table | **✅ Automatic schema display** |

---

## 💡 Core Concept: Everything is Structured Data

### Binary Schema Format

Every command outputs a schema + binary data:

```
Header:
  Magic: "PSCH" (4 bytes)
  Version: 1 (1 byte)
  Field count: N (1 byte)
  Record size: S bytes (2 bytes)

Data:
  Record count: M (4 bytes)
  Records: M × S bytes (binary)
```

### Example: Process Stream

```nim
type Process = object
  pid: int32      # offset 0
  ppid: int32     # offset 4
  memory: uint64  # offset 8
  cpu: float32    # offset 16
  # Total: 20 bytes per record
```

### Pipeline Operations

```bash
# Filter by predicate (type-safe!)
$ ps | where .memory > 1GB

# Project specific fields
$ ps | select .pid, .name

# Sort by field
$ ps | sort by .memory desc | take 10

# Aggregate
$ ps | group by .user | sum .memory

# Join streams
$ ps | join netstat on .pid

# Inspect schema
$ ps | inspect
# Shows: Schema + Binary hex dump

# Query with SQL
$ query "SELECT name, memory FROM processes WHERE cpu > 50"
```

---

## 🛠️ Quick Start

### Build Userland Utilities

```bash
# Install dependencies
sudo apt install nasm gcc ld python3

# Build all utilities
make userland

# Test them
./bin/echo          # Hello from Brainhair echo!
echo "test" | ./bin/cat
./bin/true && echo "Success: $?"
./bin/false || echo "Failed: $?"

# Try the text editor!
./bin/edit          # Opens file.txt in a beautiful CLI editor
# Type text, Backspace to delete, Ctrl+S to save, Ctrl+Q to quit
```

### Try the Type-Aware Shell! ⭐ NEW

```bash
# Launch the BrainhairOS Shell
./bin/psh

# The shell automatically detects and formats structured data!
psh> bin/ps

┌─── Schema ───────────────────────┐
│ Magic:   PSCH                     │
│ Version: 1                        │
│ Fields:  3                        │
│ RecSize: 12 bytes                 │
└──────────────────────────────────┘

┌─── Data (3 records) ───────────────┐
│ [0] 01 00 00 00 00 04 00 00 00 00 00 00  │
│ [1] 64 00 00 00 00 08 00 00 00 00 00 00  │
│ [2] c8 00 00 00 00 10 00 00 00 00 00 00  │
└──────────────────────────────────┘
```

### Try Data Pipeline (fully working!)

```bash
# Generate structured data (binary with schema)
./bin/ps | xxd
# 00000000: 5053 4348 0103 0c00 0300 0000 0100 0000  PSCH............
# 00000010: 0004 0000 0000 0000 6400 0000 0008 0000  ........d.......

# Or use the shell for automatic formatting!
echo "bin/ps" | ./bin/psh  # Pretty tables automatically!

# Inspect schema and data
./bin/ps | ./bin/inspect
# === Structured Data Stream ===
# Magic: PSCH
# Version: 01
# Fields: 03
# === Binary Data ===
# 03 00 00 00 01 00 00 00 00 04 00 00  # pid=1, mem=1024
# 64 00 00 00 00 08 00 00 00 00 00 00  # pid=100, mem=2048
# c8 00 00 00 00 10 00 00 00 00 00 00  # pid=200, mem=4096

# Filter with where command! 🎉
./bin/ps | ./bin/where | ./bin/inspect
# === Binary Data ===
# 03 00 00 00 64 00 00 00 00 08 00 00  # pid=100 (filtered out pid=1)
# c8 00 00 00 00 10 00 00 00 00 00 00  # pid=200

# Count records
./bin/ps | ./bin/count
# Record count: 3

# Compose pipelines!
./bin/ps | ./bin/where | ./bin/count
# Record count: 2  (filtered)

./bin/ps | ./bin/head | ./bin/inspect
# Shows only first record (pid=1)

./bin/ps | ./bin/tail | ./bin/inspect
# Shows only last record (pid=200)

./bin/ps | ./bin/where | ./bin/head | ./bin/inspect
# Shows first filtered record (pid=100)

./bin/ps | ./bin/where | ./bin/tail | ./bin/inspect
# Shows last filtered record (pid=200)

./bin/ps | ./bin/select | ./bin/inspect
# Projects only field 0 (pid): 1, 100, 200

./bin/ps | ./bin/where | ./bin/select | ./bin/count
# Filter then project: 2 records with 1 field each
```

### Build Kernel (optional)

```bash
# Build and run Brainhair kernel
make run-grub-brainhair

# Or just the userland
make userland
```

---

## 📁 Project Structure

```
brainhair2/
├── compiler/           # Brainhair Compiler
│   ├── brainhair.py     # Compiler driver
│   ├── lexer.py       # Tokenizer
│   ├── parser.py      # Parser (indentation-aware)
│   └── codegen_x86.py # x86 code generator
│
├── lib/               # System Libraries
│   ├── syscalls.bh   # Syscall wrappers (45+)
│   ├── syscalls.asm   # Assembly syscall stubs
│   ├── schema.bh     # Data schema definitions
│   ├── flask.bh      # Flask-style web framework
│   ├── net.bh        # Networking API
│   └── string.bh     # String utilities (split, replace, case conversion)
│
├── userland/          # Unix Utilities
│   ├── psh.bh        # ✅ Type-Aware Shell with pipelines! 🎨
│   ├── echo.bh       # ✅ Working
│   ├── cat.bh        # ✅ Working
│   ├── edit.bh       # ✅ Working (text editor)
│   ├── fbinfo.bh     # ✅ Working (framebuffer info) 🎨
│   ├── true.bh       # ✅ Working
│   ├── false.bh      # ✅ Working
│   ├── ps.bh         # ✅ Real /proc parsing!
│   ├── inspect.bh    # ✅ Working (schema viewer)
│   ├── where.bh      # ✅ Filter: where FIELD OP VALUE
│   ├── count.bh      # ✅ Working (count records)
│   ├── head.bh       # ✅ head N (take first N)
│   ├── tail.bh       # ✅ Working (take last N)
│   ├── select.bh     # ✅ Working (field projection)
│   ├── sort.bh       # ✅ sort FIELD [desc]
│   ├── fmt.bh        # ✅ Human-readable output
│   └── ls.bh         # ✅ Directory listing
│
├── bin/               # Compiled executables
│   ├── psh            # 19KB ELF32 - Type-Aware Shell with pipelines! 🎨
│   ├── echo           # 8.9KB ELF32
│   ├── cat            # 5.1KB ELF32
│   ├── edit           # 11KB ELF32 - Text Editor!
│   ├── fbinfo         # 9.6KB ELF32 - Framebuffer Info! 🎨
│   ├── true           # 4.8KB ELF32
│   ├── false          # 4.8KB ELF32
│   ├── ps             # 10.7KB ELF32 - Real /proc!
│   ├── inspect        # 9.6KB ELF32
│   ├── where          # 10.8KB ELF32
│   ├── count          # 9.4KB ELF32
│   ├── head           # 9.6KB ELF32
│   ├── tail           # 9.2KB ELF32
│   ├── select         # 9.0KB ELF32
│   ├── sort           # 10.3KB ELF32
│   ├── fmt            # 10.4KB ELF32
│   └── ls             # 9.6KB ELF32
│
├── kernel/            # BrainhairOS Microkernel
│   ├── kernel_main.bh # Entry point, scheduler, filesystem, networking
│   ├── paging.asm     # Virtual memory with dynamic page tables
│   ├── net.asm        # E1000 NIC driver, PCI enumeration
│   ├── vtnext.asm     # VTNext graphics protocol implementation
│   └── idt.asm        # Interrupt handling
│
├── boot/              # Bootloader
│   └── multiboot.asm  # GRUB multiboot
│
├── tools/             # Development & Host Tools
│   ├── vtnext_terminal.py  # VTNext graphics renderer (pygame)
│   ├── run_vtnext_tcp.sh   # Helper to run QEMU + VTNext terminal
│   └── test_vtnext_render.py # VTNext rendering test
│
└── Makefile           # Build system
```

---

## 🎯 Vision & Roadmap

### Phase 1: Core Infrastructure ✅ COMPLETE

- [x] Brainhair compiler with type system
- [x] Syscall library (45+ syscalls)
- [x] Basic utilities (echo, cat, true, false)
- [x] Binary schema format definition
- [x] Prototype structured data tools

### Phase 2: Data Pipeline ✅ COMPLETE!

- [x] **Fix binary I/O** - Address-of operator implemented ✅
- [x] **Size-aware codegen** - Proper byte/word/dword operations ✅
- [x] **Working pipeline** - ps | inspect fully functional ✅
- [x] **`where` command** - Filter by `FIELD OP VALUE` ✅
- [x] **`count` command** - Count records in stream ✅
- [x] **`head` command** - Take first N records (with args) ✅
- [x] **`tail` command** - Take last N records ✅
- [x] **`select` command** - Field projection ✅
- [x] **`psh` shell** - Type-aware shell with automatic schema detection! ✅ 🎨
- [x] **Command-line args** - argc/argv support for all utilities ✅
- [x] **`sort` command** - Sort by field ascending/descending ✅
- [x] **`fmt` command** - Human-readable output formatting ✅
- [x] **`ls` command** - Directory listing as structured data ✅
- [x] **Pipeline support in shell** - Full `cmd1 | cmd2 | cmd3` pipelines ✅
- [x] **Real /proc parsing** - ps reads actual process data ✅

### Phase 3: Query Engine

- [ ] **SQL parser** - SELECT/WHERE/GROUP BY/JOIN
- [ ] **Query optimizer** - Push-down predicates
- [ ] **Index support** - Binary search on sorted data
- [ ] **Aggregation** - SUM/COUNT/AVG/etc

### Phase 4: Virtual Filesystem

- [ ] **/proc as objects** - `Process{pid, name, mem}`
- [ ] **/net as objects** - `Interface{ip, packets}`
- [ ] **/sys as objects** - `CPU{temp, load}`
- [ ] **Live queries** - SELECT from virtual tables

### Phase 5: Advanced Features

- [ ] **Time-travel shell** - Record all commands + data
- [ ] **Schema evolution** - Handle version changes
- [ ] **Distributed queries** - Query across machines
- [ ] **Zero-copy mmap** - Shared memory pipelines

### Phase 6: Graphics & Display Server 🎨 ⬅ NEXT BIG THING

**Goal**: Build a minimal X11/Wayland-like display server from scratch

**See [DISPLAY_ROADMAP.md](DISPLAY_ROADMAP.md) for complete roadmap**

#### Sub-Phase 6.1: Framebuffer Foundation (Month 1-2) ✅ COMPLETE!
- [x] **Framebuffer access** - Direct write to `/dev/fb0` (no mmap!) ✅
- [x] **syscall6 support** - Added for mmap syscall ✅
- [x] **fbinfo utility** - Display framebuffer information ✅
- [x] **Pixel plotting** - Direct pixel manipulation via lseek+write ✅
- [x] **Graphics primitives** - Line, rect, circle drawing ✅
- [x] **clear utility** - Clear screen to solid color ✅
- [x] **Brainhair extensions** - and/or/break/continue/conditional exprs ✅
- [ ] **Text rendering** - Bitmap font support ⬅ NEXT
- [ ] **Optimized drawing** - Double buffering, fast fills
- [ ] **Sprite support** - Blit images to screen

#### Sub-Phase 6.2: Input & Events (Month 2-3)
- [ ] **Mouse support** - Read `/dev/input/mice`
- [ ] **Keyboard input** - Process keyboard events
- [ ] **Event loop** - Handle input events
- [ ] **Cursor rendering** - Mouse cursor display

#### Sub-Phase 6.3: Protocol Design (Month 3-4)
- [ ] **PoodDisplay Protocol (PDP)** - Binary protocol like X11 but simpler
- [ ] **Unix sockets** - IPC mechanism
- [ ] **Message format** - Window operations, drawing commands
- [ ] **Protocol library** - Client/server implementation

#### Sub-Phase 6.4: Display Server (Month 4-6)
- [ ] **poodd daemon** - Display server process
- [ ] **Window manager** - Multi-window support
- [ ] **Compositor** - Render windows to framebuffer
- [ ] **Client library** - libpdp for applications

#### Sub-Phase 6.5: Desktop Environment (Month 6-9)
- [ ] **Window decorations** - Title bars, borders, buttons
- [ ] **Graphical apps** - Terminal, editor, file manager
- [ ] **Desktop shell** - Taskbar, launcher, wallpaper
- [ ] **Widget toolkit** - Buttons, menus, text boxes

#### Sub-Phase 6.6: Advanced Display Features (Month 9-12)
- [ ] **Compositing effects** - Transparency, shadows, animations
- [ ] **Remote display** - Network transparency (X11-like)
- [ ] **Hardware acceleration** - DRM/KMS, OpenGL/Vulkan
- [ ] **Multi-monitor** - Support multiple displays

**Target**:
- Simpler than X11 (no legacy cruft)
- More complete than basic framebuffer
- ~100-150KB total code
- Binary protocol (fits BrainhairOS data philosophy)
- Works with existing Brainhair utilities

---

## 🔧 Development

### Build Individual Utilities

```bash
# Build specific utility
make bin/echo
make bin/cat

# Build all
make userland

# Clean
rm -rf bin/
```

### Run Tests

```bash
# Run full test suite (includes QEMU tests)
make test

# Run quick tests (no QEMU, faster)
make test-quick

# Run specific test categories
make test-userland    # Test userland utilities
make test-kernel      # Test kernel boot in QEMU
make test-http        # Test HTTP server in QEMU
```

The test suite covers:
- **Toolchain tests** - Compiler, assembler, linker availability
- **Compilation tests** - Compiling simple programs, kernel modules
- **Userland tests** - 25+ utility functionality tests
- **Kernel boot tests** - IDT, paging, scheduler, networking
- **HTTP server tests** - Flask routing, TCP connections

### Self-Hosted Toolchain

The Brainhair compiler is **self-hosting** - it can compile its own components to native x86!

#### Polyglot Compiler Architecture

The compiler is written as **polyglot code** - files that are valid in BOTH Python AND Brainhair:

```
compiler/lexer.py      - Runs as Python script OR compiles to native x86
compiler/parser.py     - Runs as Python script OR compiles to native x86
compiler/codegen_x86.py - Runs as Python script OR compiles to native x86
```

**How it works:**

1. **Python syntax subset**: The compiler uses only Python features that are also valid Brainhair:
   - Classes with methods → Brainhair classes
   - Type annotations (`-> int`, `: str`) → Brainhair types
   - Control flow (`if`, `while`, `for`) → same in Brainhair
   - `def main() -> int:` → Brainhair entry point

2. **Dual execution paths**:
   ```python
   # When run as Python:
   if __name__ == '__main__':
       lexer = Lexer(source)
       tokens = lexer.tokenize()

   # When compiled to native x86:
   def main() -> int:
       # Native entry point
       return 0
   ```

3. **Bootstrap verification**: The bootstrap script verifies correctness by:
   - Compiling test programs with Python compiler → get .asm output
   - Compiling same programs with Native compiler → get .asm output
   - **Comparing outputs - they MUST be identical**
   - Only if identical, native compiler is trusted

**Bootstrap Process:**
```bash
# Run the full bootstrap verification
./bootstrap.sh

# Output:
# ╔══════════════════════════════════════════════════════════════╗
# ║          Brainhair Bootstrap & Self-Hosting Test            ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Phase 0 - Feature Tests:
#   ✓ 141/141 tests passed
#
# Phase 1 - Compile Compiler:
#   Compiling lexer.py... OK (72660 bytes)
#   Compiling parser.py... OK (149156 bytes)
#   Compiling codegen_x86.py... OK (160780 bytes)
#   ✓ All 3 components compiled to native x86
#
# Phase 2 - Verify Native Binaries:
#   ✓ 3/3 components run successfully
#
# Phase 2.5 - Binary Comparison:
#   ✓ 138 tests match perfectly
#   ○ 3 tests differ (output matches, binary differs due to labels)
#
# ╔══════════════════════════════════════════════════════════════╗
# ║         Self-Hosting Bootstrap Completed Successfully!       ║
# ╚══════════════════════════════════════════════════════════════╝
```

**Why polyglot?**
- **No chicken-and-egg**: Python runs the first compilation
- **Verified correctness**: Output comparison proves native matches Python
- **Gradual migration**: Can run as Python during development
- **Zero external deps**: Once bootstrapped, no Python needed

**Bootstrap Options:**
```bash
./bootstrap.sh              # Full bootstrap (compile, test, build OS)
./bootstrap.sh --skip-os    # Skip OS build, just test compiler
./bootstrap.sh --verbose    # Show detailed output on mismatches
./bootstrap.sh --parallel 8 # Build 8 programs in parallel
```

**Build tools written in Brainhair:**
- basm (71KB)   - x86 assembler with SIB addressing, all x86 modes
- bhlink (24KB) - ELF32 linker with symbol resolution, R_386_PC32/R_386_32
- bhbuild (9KB) - Build orchestrator (compile → assemble → link)

**No external assembler or linker required** (except for compiler itself)!

### Recent Bug Fixes

- **basm**: Fixed `mov byte [reg+disp], reg8` encoding - was generating dword opcodes (0x89) instead of byte opcodes (0x88)
- **ls**: Fixed buffer overflow on large directories - increased allocation from 64KB to 512KB to handle 16K+ files

### Compiler Pipeline

```
source.bh → Brainhair Lexer → Tokens (with source positions)
           → Parser → AST (with span tracking)
           → Type Checker → Validated AST
           → MIR Lowering → Mid-Level IR (SSA form)
           → CodeGen → x86 Assembly (.asm)
           → basm → Object file (.o)       # Self-hosted!
           → bhlink + syscalls.o → ELF     # Self-hosted!
```

### Compiler Infrastructure (Enhanced!)

**Phase 0: Error Handling & Symbols** (Complete!)
- `compiler/errors.py` - Comprehensive error reporting with colorized output
- `compiler/spans.py` - Source location tracking (line, column, file)
- `compiler/symbols.py` - Symbol table with scoped variable/function tracking

**Phase 1: Type System** (Complete!)
- `compiler/type_checker.py` - Full type checker (988 lines!)
  - Type annotation validation
  - Expression type inference
  - Function call validation
  - Assignment compatibility
  - Struct/array type support
- Parser extensions for structs and arrays

**Phase 2: Mid-Level IR** (Complete!)
- `compiler/mir.py` - MIR data structures
  - SSA (Static Single Assignment) form
  - Basic blocks with explicit control flow
  - Typed values and operations
  - Explicit memory operations (load, store, alloca, GEP)
- `compiler/ast_to_mir.py` - AST to MIR lowering
- `compiler/mir_to_x86.py` - MIR to x86 code generation

**Test Infrastructure:**
- `compiler/tests/run_tests.py` - Custom test runner
- `compiler/tests/test_lexer.py` - 27 lexer tests
- `compiler/tests/test_parser.py` - 44 parser tests
- **71 tests passing!**

### Brainhair Language Features

- **Types**: int32, uint32, int64, uint64, float32, bool, char, ptr T
- **Control**: if/elif/else, while, for i in start..end
- **Functions**: proc with params and return types
- **Operators**: +, -, *, /, %, ==, !=, <, >, <=, >=, &, |, ^, <<, >>
- **Memory**: cast, pointer arithmetic, syscalls
- **No GC**: Manual memory (brk/mmap)

---

## 🚀 Next Steps

### Immediate Priorities

1. **Text rendering** ⬅ NEXT
   - Bitmap font support for framebuffer
   - Print strings directly to screen

2. **Enhanced shell features**
   - Command history with arrow keys
   - Tab completion
   - PATH resolution

3. **More source utilities**
   - `netstat` - Network connections as structured data
   - `df` - Disk usage
   - `free` - Memory info

### Medium Term

- **Schema versioning** - Handle format changes
- **Performance testing** - Benchmark vs Unix pipes
- **Error messages** - Better diagnostics when pipelines fail

### Long Term

- **SQL query engine** - Full relational ops
- **Distributed mode** - Query cluster nodes
- **Time-travel** - Replay command history
- ~~**Self-hosting** - Rewrite compiler in Brainhair~~ **DONE!** (lexer, parser, codegen compile to x86)

---

## 📚 Documentation

- **[VISION.md](VISION.md)** - Complete vision for data-oriented OS
- **[lib/syscalls.bh](lib/syscalls.bh)** - Available syscalls
- **[lib/schema.bh](lib/schema.bh)** - Data format specification

### Example Code

**Simple Utility (true.bh)**:
```nim
const SYS_exit: int32 = 1
extern proc syscall1(num: int32, arg1: int32): int32

proc main() =
  discard syscall1(SYS_exit, 0)
```

**Data Producer (ps.bh)**:
```nim
proc write_schema_header() =
  # Magic: "PSCH"
  discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)

  # Version: 1 (using addr operator for local variables!)
  var version: uint8 = 1
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)

  # Field count and record size...
  var field_count: uint8 = 3
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(field_count)), 1)

proc write_process_record(pid: int32, mem: int32) =
  # Binary output - no text! Using addr for safe pointer operations
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(pid)), 4)
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(mem)), 4)
```

---

## 🤝 Contributing

Want to help build the future of operating systems?

**Easy Tasks**:
- Add more basic utilities (ls, wc, grep)
- Improve shell error messages
- Add color support to shell output
- Test on different Linux distros
- Write more example pipelines

**Medium Tasks**:
- Add command-line arguments to utilities
- Implement pipeline parsing in shell
- Add real `/proc` parsing to `ps`
- Create schema validation tool
- Implement tab completion in shell
- Add command history with arrow keys

**Hard Tasks**:
- SQL query parser
- Schema evolution system
- Zero-copy mmap pipelines
- Distributed query engine

See [GitHub Issues](https://github.com/yourusername/brainhair2/issues) for specific tasks.

---

## 📜 License

**GPL-3.0** - See [LICENSE](LICENSE)

All code is free software. Fork it, hack it, improve it!

---

## 🌟 Status Summary

```
Project:    BrainhairOS - Data-Oriented Operating System
Language:   Brainhair (custom compiled language)
Runtime:    Zero dependencies (no libc, no stdlib)
Utilities:  100+ working commands + Type-Aware Shell!
Platform:   Linux x86/x86_64 (32-bit executables) + bare-metal i386
Status:     🚀 Active Development - TCP/HTTP STACK COMPLETE! 🌐

Vision:     Unix performance + PowerShell composability + Native Graphics!
Innovation: Binary typed data streams + Direct framebuffer manipulation
Goal:       Self-hosting, type-safe, zero-copy, SQL-queryable OS!

✅ Complete: Type-aware shell with automatic schema detection!
✅ Complete: Full data pipeline! (ps | where | select | head | tail | count)
✅ Complete: Graphics primitives! (clear, pixel, line, rect, circle)
✅ Complete: Full TCP/IP stack! (E1000, ARP, IP, ICMP, UDP, DHCP, TCP)
✅ Complete: Flask-style web framework (routes, query params, headers, URL encoding)!
✅ Complete: Comprehensive test suite (toolchain, userland, kernel, HTTP)
✅ Complete: Desktop environment (bds, term, fm, gedit, calc, sysmon)
✅ Complete: 100+ Unix utilities (coreutils, procutils, netutils, etc.)
✅ Complete: Compiler Phase 0-2 infrastructure (71 tests passing!)
✅ Complete: Self-hosting compiler (lexer, parser, codegen compile to native x86!)
✅ Complete: VTNext graphics protocol with Linux terminal renderer!
✅ Complete: VTNext Desktop Environment with draggable windows, Pong, Demo!

Known Limitations:
- QEMU SLiRP NAT has issues with rapid TCP port reuse
  (first HTTP request works, subsequent may timeout)
- Use TAP networking for production testing

Next:       SQL query engine → Distributed queries → Full self-hosting pipeline!
```

**Try it now**:
```bash
git clone https://github.com/yourusername/brainhair2.git
cd brainhair2
make userland

# Try the type-aware shell!
./bin/psh
psh> bin/ps
# See beautiful schema tables automatically!

# Or use classic pipelines
./bin/ps | ./bin/where | ./bin/count
echo "Hello" | ./bin/cat
```

---

**Built with ❤️ and pure x86 assembly**

*BrainhairOS - Rethinking Unix from First Principles*
