# Brainhair 2 - Gameplay Modes

The game supports **two distinct gameplay modes** using the same core engine:

## 🖥️ Terminal Mode (Direct Play)

**Files:** `play.py`, `demo.py`, `interactive_test.py`

Play directly in your terminal with a native shell experience:

```bash
python3 play.py
```

**Features:**
- Full readline support with tab completion
- Direct terminal I/O (no browser needed)
- Single-player immersive experience
- SSH between systems within the game world
- 1990s aesthetic with ASCII art intro

**Use case:** Traditional single-player hacking simulation, perfect for focused gameplay.

---

## 🌐 Web Mode (Multi-Terminal)

**File:** `web_server.py`

Play in your browser with a full desktop environment:

```bash
python3 web_server.py
```

Then open http://localhost:5000

**Features:**
- **Isolated TTY sessions** - Each terminal window has its own shell, processes, and state
- **Multiple terminals** - Open as many as you need, all properly separated
- GNOME 1-style desktop with draggable/resizable windows
- Built-in Lynx browser for in-game web browsing
- WebSocket-based real-time terminal emulation
- Perfect for demonstrations and streaming

**Use case:** Visual desktop experience, showing off to friends, or running multiple shells simultaneously.

---

## Architecture

Both modes share the same core components:

- **UnixSystem** - Virtual Unix OS with VFS, processes, permissions
- **TTY System** - Fully virtualized terminals with proper PTY pairs
- **Shell** - PooScript-based command execution
- **VirtualNetwork** - Packet-based networking with SSH, routing, firewalls
- **World (1990)** - December 1990 internet with missions and challenges

### Key Difference

**Terminal Mode:**
- Uses single shared Shell instance (play.py:53-157)
- Direct stdin/stdout via Python's `input()` and `print()`
- One player session per process

**Web Mode:**
- Creates isolated Shell instance per browser terminal (web_server.py:55-109)
- WebSocket communication with per-terminal routing
- Multiple concurrent terminals with proper separation
- Session-based state management

---

## Recent Fixes (2025-10-16)

Fixed critical TTY separation issues in web mode:

1. ✅ Each terminal now gets its own Shell instance
2. ✅ Proper shell initialization before accepting input
3. ✅ Input/output routing with shell_id filtering
4. ✅ Clean resource cleanup when terminals close

Terminal mode was unaffected and continues to work perfectly.

---

## Try Both!

**Quick terminal session:**
```bash
python3 play.py
```

**Full web experience:**
```bash
python3 web_server.py
# Open http://localhost:5000
# Double-click Terminal icon to create shells
```

Both modes give you the full 1990s hacking experience! 🎮
