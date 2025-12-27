#!/usr/bin/env python3
"""
VTNext Terminal - A graphical terminal for BrainhairOS VTNext protocol

Connects via serial or network and renders VTNext graphics commands.

Usage:
    ./vtnext_terminal.py --serial /dev/ttyUSB0
    ./vtnext_terminal.py --serial /dev/pts/X  (for QEMU)
    ./vtnext_terminal.py --tcp localhost:1234
    ./vtnext_terminal.py --stdin  (read from stdin, useful with socat)
"""

import sys
import os
import re
import argparse
import threading
import queue
import time

try:
    import pygame
    from pygame import gfxdraw
except ImportError:
    print("pygame not found. Install with: pip install pygame")
    sys.exit(1)

try:
    import serial
except ImportError:
    serial = None  # Optional, for serial port support

# Window dimensions
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768

# VTNext command regex: ESC ] vtn ; command ; params BEL
# Format: \x1b]vtn;command;params\x07
VTNEXT_PATTERN = re.compile(r'\x1b\]vtn;([^;\x07]+);?([^\x07]*)\x07')

class VTNextTerminal:
    def __init__(self, log_file=None, debug=False):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("VTNext Terminal - BrainhairOS")

        self.clock = pygame.time.Clock()
        self.running = True
        self.cursor_visible = True
        self.cursor_x = 0
        self.cursor_y = 0

        # Background color (RGBA, but we use RGB for display)
        self.bg_color = (0, 0, 0)

        # Text buffer for regular terminal output
        self.text_lines = []
        self.current_line = ""

        # Fonts - try to find a good monospace font
        self.fonts = {}
        self.load_fonts()

        # Command queue from reader thread
        self.cmd_queue = queue.Queue()

        # Buffer for incomplete escape sequences
        self.buffer = ""

        # Layers for graphics (layer 0 = background, higher = foreground)
        self.layers = {}

        # Mouse state for cursor rendering
        self.mouse_x = WINDOW_WIDTH // 2
        self.mouse_y = WINDOW_HEIGHT // 2
        self.mouse_buttons = 0  # Bit flags: 1=left, 2=middle, 4=right
        self.last_mouse_send = 0  # Throttle mouse move events

        # Graphics mode (False = show terminal text, True = show graphics)
        self.graphics_mode = False

        # Double buffering - draw to back buffer, flip on clear
        self.back_buffer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.back_buffer.fill((0, 0, 0))

        # Logging
        self.log_file = None
        self.debug = debug
        if log_file:
            self.log_file = open(log_file, 'a')
            self.log("=== VTNext Terminal Started ===")

        # Enable key repeat for held keys (delay 200ms, repeat every 50ms)
        pygame.key.set_repeat(200, 50)

        # Clear the screen initially
        self.screen.fill(self.bg_color)
        pygame.display.flip()

    def log(self, msg):
        """Write to log file"""
        if self.log_file:
            self.log_file.write(f"{msg}\n")
            self.log_file.flush()
        if self.debug:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def log_command(self, cmd, params):
        """Log a VTNext command"""
        self.log(f"VTN: {cmd};{params}")

    def load_fonts(self):
        """Load fonts for text rendering"""
        font_names = ['DejaVu Sans Mono', 'Liberation Mono', 'Courier New', 'monospace']

        for size in [12, 14, 16, 18, 20, 24, 28, 32, 48]:
            font = None
            for name in font_names:
                try:
                    font = pygame.font.SysFont(name, size)
                    break
                except:
                    continue
            if font is None:
                font = pygame.font.Font(None, size)
            self.fonts[size] = font

        # Default font
        self.default_font = self.fonts.get(16, pygame.font.Font(None, 16))

    def get_font(self, font_id, scale):
        """Get font by ID and scale"""
        # font_id 0 = normal, 1 = bold (we just use size)
        base_size = 16
        size = int(base_size * scale)

        # Find closest available size
        available = sorted(self.fonts.keys())
        closest = min(available, key=lambda x: abs(x - size))
        return self.fonts[closest]

    def parse_vtnext(self, data):
        """Parse VTNext escape sequences from data"""
        self.buffer += data

        # Find all complete VTNext commands
        while True:
            match = VTNEXT_PATTERN.search(self.buffer)
            if not match:
                # Check for incomplete escape sequence at end
                esc_pos = self.buffer.rfind('\x1b')
                if esc_pos >= 0 and esc_pos > len(self.buffer) - 100:
                    # Keep potential incomplete sequence
                    regular_text = self.buffer[:esc_pos]
                    self.buffer = self.buffer[esc_pos:]
                else:
                    regular_text = self.buffer
                    self.buffer = ""

                # Handle regular terminal text
                if regular_text:
                    self.handle_text(regular_text)
                break

            # Handle text before the command
            if match.start() > 0:
                self.handle_text(self.buffer[:match.start()])

            # Handle the VTNext command
            cmd = match.group(1)
            params = match.group(2) if match.group(2) else ""
            self.handle_vtnext_command(cmd, params)

            # Remove processed part
            self.buffer = self.buffer[match.end():]

    def handle_text(self, text):
        """Handle regular terminal text output"""
        # Filter out other escape sequences
        text = re.sub(r'\x1b\[[^m]*m', '', text)  # ANSI colors
        text = re.sub(r'\x1b\[\?[0-9]+[hl]', '', text)  # Mode changes
        text = re.sub(r'\x1bc', '', text)  # Reset
        text = re.sub(r'\x1b\[2J', '', text)  # Clear screen

        for char in text:
            if char == '\n':
                self.text_lines.append(self.current_line)
                self.current_line = ""
                # Keep only last 100 lines
                if len(self.text_lines) > 100:
                    self.text_lines = self.text_lines[-100:]
            elif char == '\r':
                self.current_line = ""  # Carriage return clears current line
            elif ord(char) >= 32 or char == '\t':
                self.current_line += char

        # Detect shell prompt to switch back to text mode
        if self.graphics_mode:
            full_text = '\n'.join(self.text_lines[-5:]) + self.current_line
            if 'bhos>' in full_text or 'App exited' in full_text:
                self.graphics_mode = False
                self.screen.fill((0, 0, 0))

    def handle_vtnext_command(self, cmd, params):
        """Handle a VTNext graphics command"""
        self.log_command(cmd, params)
        parts = params.split(';') if params else []

        try:
            if cmd == 'clear':
                # clear;r;g;b;a - clear back buffer and start new frame
                if len(parts) >= 4:
                    r, g, b, a = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                    self.bg_color = (r, g, b)
                    self.back_buffer.fill(self.bg_color)
                    self.layers.clear()
                    self.text_lines.clear()
                    self.current_line = ""
                    self.graphics_mode = True  # Switch to graphics mode

            elif cmd == 'present':
                # present - flip buffers to show completed frame
                self.screen.blit(self.back_buffer, (0, 0))
                pygame.display.flip()

            elif cmd == 'cursor':
                # cursor;show or cursor;hide
                if parts and parts[0] == 'hide':
                    self.cursor_visible = False
                elif parts and parts[0] == 'show':
                    self.cursor_visible = True

            elif cmd == 'input':
                # input;raw or input;cooked
                pass  # Terminal mode, not much to do here

            elif cmd == 'rect':
                # rect;x;y;layer;w;h;filled;r;g;b;a;filled
                # From output: rect;50;100;1;120;80;0;255;100;100;200;1
                if len(parts) >= 11:
                    x, y = int(parts[0]), int(parts[1])
                    layer = int(parts[2])
                    w, h = int(parts[3]), int(parts[4])
                    # parts[5] seems redundant, skip
                    r, g, b, a = int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9])
                    filled = int(parts[10]) if len(parts) > 10 else 1

                    color = (r, g, b)
                    if filled:
                        pygame.draw.rect(self.back_buffer, color, (x, y, w, h))
                    else:
                        pygame.draw.rect(self.back_buffer, color, (x, y, w, h), 2)

            elif cmd == 'circle':
                # circle;x;y;layer;radius;r;g;b;a;filled
                if len(parts) >= 9:
                    x, y = int(parts[0]), int(parts[1])
                    layer = int(parts[2])
                    radius = int(parts[3])
                    r, g, b, a = int(parts[4]), int(parts[5]), int(parts[6]), int(parts[7])
                    filled = int(parts[8]) if len(parts) > 8 else 1

                    color = (r, g, b)
                    if filled:
                        pygame.draw.circle(self.back_buffer, color, (x, y), radius)
                    else:
                        pygame.draw.circle(self.back_buffer, color, (x, y), radius, 2)

            elif cmd == 'line':
                # line;x1;y1;x2;y2;layer;thickness;r;g;b;a
                if len(parts) >= 10:
                    x1, y1 = int(parts[0]), int(parts[1])
                    x2, y2 = int(parts[2]), int(parts[3])
                    layer = int(parts[4])
                    thickness = int(parts[5])
                    r, g, b, a = int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9])

                    color = (r, g, b)
                    pygame.draw.line(self.back_buffer, color, (x1, y1), (x2, y2), max(1, thickness))

            elif cmd == 'rrect':
                # rrect;x;y;layer;w;h;radius;r;g;b;a;filled
                if len(parts) >= 11:
                    x, y = int(parts[0]), int(parts[1])
                    layer = int(parts[2])
                    w, h = int(parts[3]), int(parts[4])
                    radius = int(parts[5])
                    r, g, b, a = int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9])
                    filled = int(parts[10]) if len(parts) > 10 else 1

                    color = (r, g, b)
                    rect = pygame.Rect(x, y, w, h)
                    if filled:
                        pygame.draw.rect(self.back_buffer, color, rect, border_radius=radius)
                    else:
                        pygame.draw.rect(self.back_buffer, color, rect, 2, border_radius=radius)

            elif cmd == 'text':
                # text;x;y;layer;font;scale;r;g;b;a;"text"
                # The text is quoted at the end
                if len(parts) >= 10:
                    x, y = int(parts[0]), int(parts[1])
                    layer = int(parts[2])
                    font_id = int(parts[3])
                    scale = float(parts[4])
                    r, g, b, a = int(parts[5]), int(parts[6]), int(parts[7]), int(parts[8])

                    # Get text - it's quoted and may contain semicolons
                    text_part = ';'.join(parts[9:])
                    # Remove quotes
                    if text_part.startswith('"') and text_part.endswith('"'):
                        text_part = text_part[1:-1]

                    color = (r, g, b)
                    font = self.get_font(font_id, scale)
                    text_surface = font.render(text_part, True, color)
                    # Position text with x,y as top-left corner
                    self.back_buffer.blit(text_surface, (x, y))

            elif cmd == 'sprite':
                # sprite;id;x;y;layer - draw a sprite
                pass  # TODO: sprite support

            elif cmd == 'anim':
                # anim;id;x;y;layer;frame - draw animation frame
                pass  # TODO: animation support

        except (ValueError, IndexError) as e:
            print(f"VTNext parse error: {cmd};{params}: {e}", file=sys.stderr)

    def render_terminal_text(self):
        """Render regular terminal text (top to bottom, like a terminal)"""
        font = self.default_font
        line_height = font.get_linesize()

        # Calculate how many lines can fit
        max_lines = (WINDOW_HEIGHT - 20) // line_height

        # Get visible lines (including current line)
        all_lines = self.text_lines + ([self.current_line] if self.current_line else [])
        visible_lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines

        y = 10
        for i, line in enumerate(visible_lines):
            # Use brighter color for current line
            if i == len(visible_lines) - 1 and self.current_line:
                color = (0, 255, 0)  # Green for current line
            else:
                color = (200, 200, 200)

            text_surface = font.render(line[:150], True, color)  # Limit line length
            self.screen.blit(text_surface, (10, y))
            y += line_height

    def run(self, input_source):
        """Main event loop"""
        self.input_source = input_source
        reader_thread = threading.Thread(target=self.reader_loop, args=(input_source,), daemon=True)
        reader_thread.start()

        # Track if we're in graphics mode or text mode
        self.graphics_mode = False

        while self.running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    # Ctrl+Q to quit terminal (not just Q)
                    if event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL):
                        self.running = False
                    else:
                        # Send keypress to serial/TCP
                        self.send_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Send click event to OS (simpler than down/up)
                    x, y = event.pos
                    self.mouse_x, self.mouse_y = x, y
                    button = event.button  # 1=left, 2=middle, 3=right
                    self.mouse_buttons |= (1 << (button - 1))
                    if button == 1:  # Only send left clicks
                        self.send_mouse_click(x, y, button)
                elif event.type == pygame.MOUSEBUTTONUP:
                    x, y = event.pos
                    self.mouse_x, self.mouse_y = x, y
                    button = event.button
                    self.mouse_buttons &= ~(1 << (button - 1))
                    if button == 1:  # Left button released
                        self.send_mouse_up(x, y, button)
                elif event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    self.mouse_x, self.mouse_y = x, y
                    # Send move events while dragging (left button held)
                    if self.mouse_buttons & 1:
                        now = time.time()
                        # Throttle to ~30 move events per second
                        if now - self.last_mouse_send > 0.033:
                            self.send_mouse_move(x, y)
                            self.last_mouse_send = now

            # Process commands from reader thread
            try:
                while True:
                    data = self.cmd_queue.get_nowait()
                    self.parse_vtnext(data)
            except queue.Empty:
                pass

            # In text mode, render terminal text and flip
            if not self.graphics_mode:
                self.screen.fill((0, 0, 0))
                self.render_terminal_text()
                pygame.display.flip()
            # In graphics mode, flip happens on 'clear' command

            self.clock.tick(60)

        pygame.quit()

    def send_key(self, event):
        """Send a keypress to the serial/TCP connection"""
        key = event.key
        char = None

        # Map special keys
        if key == pygame.K_RETURN:
            char = '\r'
        elif key == pygame.K_BACKSPACE:
            char = '\x7f'
        elif key == pygame.K_DELETE:
            char = '\x1b[3~'
        elif key == pygame.K_TAB:
            char = '\t'
        elif key == pygame.K_UP:
            char = '\x1b[A'
        elif key == pygame.K_DOWN:
            char = '\x1b[B'
        elif key == pygame.K_RIGHT:
            char = '\x1b[C'
        elif key == pygame.K_LEFT:
            char = '\x1b[D'
        elif key == pygame.K_HOME:
            char = '\x1b[H'
        elif key == pygame.K_END:
            char = '\x1b[F'
        elif key == pygame.K_PAGEUP:
            char = '\x1b[5~'
        elif key == pygame.K_PAGEDOWN:
            char = '\x1b[6~'
        elif key == pygame.K_F1:
            char = '\x1bOP'
        elif key == pygame.K_F2:
            char = '\x1bOQ'
        elif key == pygame.K_F3:
            char = '\x1bOR'
        elif key == pygame.K_F4:
            char = '\x1bOS'
        elif event.unicode and ord(event.unicode) >= 32 and ord(event.unicode) < 127:
            char = event.unicode
        elif event.unicode and ord(event.unicode) < 32:
            # Control characters (Ctrl+C, etc.)
            char = event.unicode

        if char and hasattr(self, 'input_source'):
            try:
                data = char.encode('utf-8') if isinstance(char, str) else char
                if hasattr(self.input_source, 'sock'):
                    # TCP
                    sent = self.input_source.sock.send(data)
                    self.log(f"KEY SEND: {repr(char)} -> {sent} bytes")
                elif hasattr(self.input_source, 'write'):
                    # Serial or file
                    self.input_source.write(data)
                    if hasattr(self.input_source, 'flush'):
                        self.input_source.flush()
                    self.log(f"KEY SEND: {repr(char)}")
            except Exception as e:
                self.log(f"KEY SEND ERROR: {e}")
                print(f"Send error: {e}", file=sys.stderr)

    def send_mouse_event(self, event_type, x, y, button=0):
        """Send mouse event to the OS"""
        # Format: ESC ] vtn ; type ; x ; y ; button BEL
        if button:
            msg = f"\x1b]vtn;{event_type};{x};{y};{button}\x07"
        else:
            msg = f"\x1b]vtn;{event_type};{x};{y}\x07"
        try:
            data = msg.encode('utf-8')
            if hasattr(self, 'input_source'):
                if hasattr(self.input_source, 'sock'):
                    sent = self.input_source.sock.send(data)
                    self.log(f"SEND: {len(data)} bytes sent ({sent} actual): {repr(msg)}")
                elif hasattr(self.input_source, 'write'):
                    self.input_source.write(data)
                    if hasattr(self.input_source, 'flush'):
                        self.input_source.flush()
                    self.log(f"SEND: {len(data)} bytes written: {repr(msg)}")
            else:
                self.log(f"SEND ERROR: no input_source")
        except Exception as e:
            self.log(f"SEND ERROR: {e}")

    def send_mouse_click(self, x, y, button):
        """Send mouse click event to the OS (legacy)"""
        self.log(f"MOUSE: click at ({x}, {y}) button {button}")
        self.send_mouse_event('click', x, y, button)

    def send_mouse_down(self, x, y, button):
        """Send mouse button down event"""
        self.log(f"MOUSE: down at ({x}, {y}) button {button}")
        self.send_mouse_event('down', x, y, button)

    def send_mouse_up(self, x, y, button):
        """Send mouse button up event"""
        self.log(f"MOUSE: up at ({x}, {y}) button {button}")
        self.send_mouse_event('up', x, y, button)

    def send_mouse_move(self, x, y):
        """Send mouse move event"""
        self.send_mouse_event('move', x, y)

    def draw_cursor(self):
        """Draw mouse cursor on screen"""
        x, y = self.mouse_x, self.mouse_y

        # Draw arrow cursor (white with black outline)
        # Arrow shape points
        points = [
            (x, y),           # Tip
            (x, y + 16),      # Bottom left
            (x + 4, y + 12),  # Inner corner
            (x + 10, y + 18), # Bottom point
            (x + 12, y + 16), # Right of bottom point
            (x + 6, y + 10),  # Inner right
            (x + 11, y + 5),  # Right edge
        ]

        # Draw black outline
        pygame.draw.polygon(self.screen, (0, 0, 0), points, 2)
        # Draw white fill
        pygame.draw.polygon(self.screen, (255, 255, 255), points)

    def reader_loop(self, input_source):
        """Read data from input source and queue commands"""
        try:
            while self.running:
                if hasattr(input_source, 'read'):
                    # File-like object (stdin, serial, socket)
                    data = input_source.read(1024)
                    if not data:
                        time.sleep(0.01)
                        continue
                    if isinstance(data, bytes):
                        data = data.decode('utf-8', errors='replace')
                    # Log raw data (escape non-printable chars)
                    if self.debug and data:
                        safe = data.replace('\x1b', '<ESC>').replace('\x07', '<BEL>')
                        self.log(f"RAW: {repr(safe[:200])}")
                    self.cmd_queue.put(data)
                else:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Reader error: {e}", file=sys.stderr)


def open_serial(port, baudrate=115200):
    """Open serial port"""
    if serial is None:
        print("pyserial not installed. Install with: pip install pyserial")
        sys.exit(1)
    return serial.Serial(port, baudrate, timeout=0.1)


class TCPReader:
    """TCP socket reader with timeout"""
    def __init__(self, host, port):
        import socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(0.1)

    def read(self, size=1024):
        import socket
        try:
            data = self.sock.recv(size)
            return data.decode('utf-8', errors='replace')
        except socket.timeout:
            return ""
        except Exception:
            return ""

    def close(self):
        self.sock.close()


def open_tcp(host, port):
    """Open TCP connection"""
    return TCPReader(host, port)


def open_pty_pair():
    """Create a PTY pair for QEMU connection"""
    import pty
    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    print(f"PTY slave: {slave_name}")
    print(f"Connect QEMU with: -serial {slave_name}")
    return os.fdopen(master, 'rb')


def main():
    parser = argparse.ArgumentParser(description='VTNext Terminal for BrainhairOS')
    parser.add_argument('--serial', '-s', help='Serial port (e.g., /dev/ttyUSB0)')
    parser.add_argument('--tcp', '-t', help='TCP host:port (e.g., localhost:1234)')
    parser.add_argument('--stdin', '-i', action='store_true', help='Read from stdin')
    parser.add_argument('--pty', '-p', action='store_true', help='Create PTY pair for QEMU')
    parser.add_argument('--baudrate', '-b', type=int, default=115200, help='Serial baudrate')
    parser.add_argument('--file', '-f', help='Read from file (for testing)')
    parser.add_argument('--log', '-l', help='Log file for raw VTNext commands')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    input_source = None

    if args.serial:
        print(f"Opening serial port: {args.serial}")
        input_source = open_serial(args.serial, args.baudrate)
    elif args.tcp:
        host, port = args.tcp.split(':')
        print(f"Connecting to {host}:{port}")
        input_source = open_tcp(host, int(port))
    elif args.stdin:
        print("Reading from stdin...")
        input_source = sys.stdin
    elif args.pty:
        print("Creating PTY pair...")
        input_source = open_pty_pair()
    elif args.file:
        print(f"Reading from file: {args.file}")
        input_source = open(args.file, 'r')
    else:
        parser.print_help()
        print("\nExample with QEMU:")
        print("  # Terminal 1: Start QEMU with serial")
        print("  qemu-system-i386 -drive file=build/brainhair.img,format=raw -serial pty")
        print("  # Note the PTY path it prints (e.g., /dev/pts/5)")
        print()
        print("  # Terminal 2: Connect VTNext terminal")
        print("  ./vtnext_terminal.py --serial /dev/pts/5")
        print()
        print("Or use TCP:")
        print("  qemu-system-i386 ... -serial tcp:localhost:5555,server,nowait")
        print("  ./vtnext_terminal.py --tcp localhost:5555")
        sys.exit(1)

    terminal = VTNextTerminal(log_file=args.log, debug=args.debug)
    terminal.run(input_source)


if __name__ == '__main__':
    main()
