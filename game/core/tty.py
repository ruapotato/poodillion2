#!/usr/bin/env python3
"""
Virtual TTY (Teletypewriter) System
Provides fully virtualized terminal devices with proper terminal attributes,
line discipline, and PTY support.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
import time


@dataclass
class TerminalAttributes:
    """Terminal attributes (termios-like)"""

    # Input modes
    icrnl: bool = True      # Map CR to NL on input
    igncr: bool = False     # Ignore CR
    inlcr: bool = False     # Map NL to CR on input
    istrip: bool = False    # Strip 8th bit

    # Output modes
    opost: bool = True      # Post-process output
    onlcr: bool = True      # Map NL to CR-NL on output
    ocrnl: bool = False     # Map CR to NL on output

    # Control modes
    csize: int = 8          # Character size (5-8 bits)
    parenb: bool = False    # Parity enable
    parodd: bool = False    # Odd parity

    # Local modes
    echo: bool = True       # Echo input characters
    echoe: bool = True      # Echo ERASE as BS-SP-BS
    echok: bool = True      # Echo KILL
    icanon: bool = True     # Canonical mode (line buffering)
    isig: bool = True       # Enable signals

    # Control characters
    vintr: int = 3          # ^C - interrupt
    vquit: int = 28         # ^\ - quit
    verase: int = 127       # DEL or ^H - erase
    vkill: int = 21         # ^U - kill line
    veof: int = 4           # ^D - end of file
    vsusp: int = 26         # ^Z - suspend

    # Terminal size
    rows: int = 24
    cols: int = 80


@dataclass
class TTY:
    """Virtual TTY device"""

    name: str                           # e.g., "tty1", "pts/0"
    number: int                         # TTY number
    attrs: TerminalAttributes = field(default_factory=TerminalAttributes)

    # Buffers
    input_buffer: bytearray = field(default_factory=bytearray)
    output_buffer: bytearray = field(default_factory=bytearray)
    line_buffer: bytearray = field(default_factory=bytearray)  # For canonical mode

    # State
    foreground_pgrp: Optional[int] = None  # Foreground process group
    session_leader: Optional[int] = None   # Session leader PID
    controlling_process: Optional[int] = None

    # Flags
    is_pty: bool = False                # Is this a pseudo-terminal?
    master_fd: Optional[int] = None     # Master side (for PTY)
    slave_fd: Optional[int] = None      # Slave side (for PTY)

    # Statistics
    created_at: float = field(default_factory=time.time)
    last_input: float = field(default_factory=time.time)
    last_output: float = field(default_factory=time.time)

    def write(self, data: bytes) -> int:
        """Write data to TTY output"""
        if self.attrs.opost:
            # Post-process output
            processed = bytearray()
            for byte in data:
                if byte == ord('\n') and self.attrs.onlcr:
                    # Map NL to CR-NL
                    processed.append(ord('\r'))
                    processed.append(ord('\n'))
                elif byte == ord('\r') and self.attrs.ocrnl:
                    # Map CR to NL
                    processed.append(ord('\n'))
                else:
                    processed.append(byte)
            data = bytes(processed)

        self.output_buffer.extend(data)
        self.last_output = time.time()
        return len(data)

    def read(self, max_bytes: int = -1) -> bytes:
        """Read data from TTY input"""
        if self.attrs.icanon:
            # Canonical mode - read line by line
            if b'\n' not in self.input_buffer and b'\x04' not in self.input_buffer:
                return b''  # No complete line yet

            # Find line ending
            nl_idx = self.input_buffer.find(b'\n')
            eof_idx = self.input_buffer.find(b'\x04')

            if nl_idx != -1 and (eof_idx == -1 or nl_idx < eof_idx):
                # Read until newline (inclusive)
                data = bytes(self.input_buffer[:nl_idx + 1])
                self.input_buffer = self.input_buffer[nl_idx + 1:]
            elif eof_idx != -1:
                # Read until EOF (exclusive)
                data = bytes(self.input_buffer[:eof_idx])
                self.input_buffer = self.input_buffer[eof_idx + 1:]
            else:
                data = b''
        else:
            # Non-canonical mode - read raw
            if max_bytes == -1:
                data = bytes(self.input_buffer)
                self.input_buffer.clear()
            else:
                data = bytes(self.input_buffer[:max_bytes])
                self.input_buffer = self.input_buffer[max_bytes:]

        if data:
            self.last_input = time.time()

        return data

    def read_output(self, max_bytes: int = -1) -> bytes:
        """Read data from TTY output buffer (for display)"""
        if max_bytes == -1:
            data = bytes(self.output_buffer)
            self.output_buffer.clear()
        else:
            data = bytes(self.output_buffer[:max_bytes])
            self.output_buffer = self.output_buffer[max_bytes:]

        return data

    def process_input(self, data: bytes) -> bytes:
        """Process input data through line discipline"""
        result = bytearray()

        for byte in data:
            # Input processing
            if self.attrs.istrip:
                byte = byte & 0x7F

            # Map CR/NL
            if byte == ord('\r'):
                if self.attrs.igncr:
                    continue
                if self.attrs.icrnl:
                    byte = ord('\n')
            elif byte == ord('\n'):
                if self.attrs.inlcr:
                    byte = ord('\r')

            # Check for special characters in canonical mode
            if self.attrs.icanon:
                if byte == self.attrs.verase:
                    # Backspace/erase
                    if self.line_buffer:
                        self.line_buffer.pop()
                        if self.attrs.echo and self.attrs.echoe:
                            self.write(b'\b \b')
                    continue
                elif byte == self.attrs.vkill:
                    # Kill line
                    if self.attrs.echo and self.attrs.echok:
                        self.write(b'\n')
                    self.line_buffer.clear()
                    continue
                elif byte == ord('\n') or byte == self.attrs.veof:
                    # End of line or EOF
                    if byte == ord('\n'):
                        self.line_buffer.append(byte)
                    self.input_buffer.extend(self.line_buffer)
                    self.line_buffer.clear()
                    if self.attrs.echo:
                        self.write(bytes([byte]))
                    continue

            # Signal handling
            if self.attrs.isig:
                if byte == self.attrs.vintr:
                    # ^C - SIGINT
                    result.append(byte)
                    # TODO: Send SIGINT to foreground process group
                    continue
                elif byte == self.attrs.vsusp:
                    # ^Z - SIGTSTP
                    # TODO: Send SIGTSTP to foreground process group
                    continue
                elif byte == self.attrs.vquit:
                    # ^\ - SIGQUIT
                    # TODO: Send SIGQUIT to foreground process group
                    continue

            # Add to buffer
            if self.attrs.icanon:
                self.line_buffer.append(byte)
                if self.attrs.echo:
                    self.write(bytes([byte]))
            else:
                self.input_buffer.append(byte)
                if self.attrs.echo:
                    self.write(bytes([byte]))

        return bytes(result)

    def set_size(self, rows: int, cols: int):
        """Set terminal size (TIOCSWINSZ)"""
        self.attrs.rows = rows
        self.attrs.cols = cols
        # TODO: Send SIGWINCH to foreground process group

    def get_size(self) -> tuple[int, int]:
        """Get terminal size (TIOCGWINSZ)"""
        return (self.attrs.rows, self.attrs.cols)


class TTYManager:
    """Manages all TTY devices in the system"""

    def __init__(self):
        self.ttys: Dict[str, TTY] = {}
        self.tty_counter = 0
        self.pts_counter = 0

    def create_tty(self, name: Optional[str] = None) -> TTY:
        """Create a new TTY device"""
        if name is None:
            self.tty_counter += 1
            name = f"tty{self.tty_counter}"

        tty = TTY(name=name, number=self.tty_counter)
        self.ttys[name] = tty
        return tty

    def create_pty(self) -> tuple[TTY, TTY]:
        """Create a PTY (pseudo-terminal) pair (master, slave)"""
        self.pts_counter += 1

        # Create master
        master = TTY(
            name=f"ptm{self.pts_counter}",
            number=self.pts_counter,
            is_pty=True
        )

        # Create slave
        slave = TTY(
            name=f"pts/{self.pts_counter}",
            number=self.pts_counter,
            is_pty=True
        )

        # Link them
        master.slave_fd = self.pts_counter
        slave.master_fd = self.pts_counter

        self.ttys[master.name] = master
        self.ttys[slave.name] = slave

        return master, slave

    def get_tty(self, name: str) -> Optional[TTY]:
        """Get TTY by name"""
        return self.ttys.get(name)

    def list_ttys(self) -> List[TTY]:
        """List all TTYs"""
        return list(self.ttys.values())

    def delete_tty(self, name: str):
        """Delete a TTY"""
        if name in self.ttys:
            del self.ttys[name]
