# reset - Reset terminal to sane state
# Usage: reset
# Sends terminal reset sequence and restores sane settings
# Combines terminal reset + stty sane

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_ioctl: int32 = 54

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

# ioctl commands for terminal control
const TCGETS: int32 = 0x5401
const TCSETS: int32 = 0x5402

# termios flags
const ECHO: int32 = 0x0008
const ICANON: int32 = 0x0002
const ISIG: int32 = 0x0001
const ICRNL: int32 = 0x0100
const IXON: int32 = 0x0400
const OPOST: int32 = 0x0001

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc main() =
  # Allocate memory for termios structure
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 256
  discard syscall1(SYS_brk, new_brk)

  var termios: ptr int32 = cast[ptr int32](old_brk)

  # Send terminal reset sequences
  # ESC c - Full reset (RIS - Reset to Initial State)
  print(cast[ptr uint8]("\x1bc"))

  # ESC[!p - Soft terminal reset
  print(cast[ptr uint8]("\x1b[!p"))

  # ESC[?25h - Show cursor
  print(cast[ptr uint8]("\x1b[?25h"))

  # Clear screen and home cursor
  print(cast[ptr uint8]("\x1b[2J\x1b[H"))

  # Get current terminal attributes
  var ret: int32 = syscall3(SYS_ioctl, STDIN, TCGETS, cast[int32](termios))

  if ret >= 0:
    # Reset to sane defaults
    # Enable: echo, canonical, signals, output processing
    termios[3] = termios[3] | ECHO | ICANON | ISIG
    termios[0] = termios[0] | ICRNL | IXON
    termios[1] = termios[1] | OPOST

    # Apply settings
    ret = syscall3(SYS_ioctl, STDIN, TCSETS, cast[int32](termios))

  # Print a newline to ensure clean state
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
