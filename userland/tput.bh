# tput - Terminal capabilities
# Usage: tput [CAPABILITY] [ARGS...]
#   tput clear        - Clear screen
#   tput cols         - Print number of columns
#   tput lines        - Print number of rows
#   tput cup Y X      - Move cursor to row Y, column X
# Outputs ANSI escape codes

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_ioctl: int32 = 54

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

# ioctl commands for window size
const TIOCGWINSZ: int32 = 0x5413

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

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

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s2[i] == cast[uint8](0):
      return 1
    if s1[i] != s2[i]:
      var diff: int32 = cast[int32](s1[i]) - cast[int32](s2[i])
      return diff
    i = i + 1
  if s2[i] != cast[uint8](0):
    return -1
  return 0

# Parse integer from string
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0

  while s[i] != cast[uint8](0):
    var c: uint8 = s[i]
    if c >= cast[uint8](48):
      if c <= cast[uint8](57):
        var digit: int32 = cast[int32](c) - 48
        result = result * 10 + digit
        i = i + 1
      if c > cast[uint8](57):
        return -1
    if c < cast[uint8](48):
      return -1

  return result

# Print integer as string
proc print_int(n: int32) =
  var buf: ptr uint8
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16
  discard syscall1(SYS_brk, new_brk)
  buf = cast[ptr uint8](old_brk)

  if n == 0:
    buf[0] = cast[uint8](48)
    buf[1] = cast[uint8](0)
    print(buf)
    return

  var num: int32 = n
  var i: int32 = 0

  # Handle negative numbers
  var is_negative: int32 = 0
  if num < 0:
    is_negative = 1
    num = -num

  # Build string in reverse
  while num > 0:
    var digit: int32 = num % 10
    buf[i] = cast[uint8](48 + digit)
    num = num / 10
    i = i + 1

  if is_negative != 0:
    buf[i] = cast[uint8](45)  # '-'
    i = i + 1

  buf[i] = cast[uint8](0)

  # Reverse the string
  var start: int32 = 0
  var end: int32 = i - 1
  while start < end:
    var temp: uint8 = buf[start]
    buf[start] = buf[end]
    buf[end] = temp
    start = start + 1
    end = end - 1

  print(buf)

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    print_err(cast[ptr uint8]("Usage: tput CAPABILITY [ARGS...]\n"))
    print_err(cast[ptr uint8]("  clear      - Clear screen\n"))
    print_err(cast[ptr uint8]("  cols       - Print columns\n"))
    print_err(cast[ptr uint8]("  lines      - Print rows\n"))
    print_err(cast[ptr uint8]("  cup Y X    - Move cursor to row Y, column X\n"))
    discard syscall1(SYS_exit, 1)

  var capability: ptr uint8 = get_argv(1)

  # clear - clear screen
  var cmp_clear: int32 = strcmp(capability, cast[ptr uint8]("clear"))
  if cmp_clear == 0:
    # ANSI escape: ESC[2J (clear screen) ESC[H (home cursor)
    print(cast[ptr uint8]("\x1b[2J\x1b[H"))
    discard syscall1(SYS_exit, 0)

  # cols - get terminal width
  var cmp_cols: int32 = strcmp(capability, cast[ptr uint8]("cols"))
  if cmp_cols == 0:
    # Allocate winsize struct (8 bytes: rows, cols, xpixel, ypixel)
    var old_brk: int32 = syscall1(SYS_brk, 0)
    var new_brk: int32 = old_brk + 16
    discard syscall1(SYS_brk, new_brk)
    var winsize: ptr int32 = cast[ptr int32](old_brk)

    var ret: int32 = syscall3(SYS_ioctl, STDOUT, TIOCGWINSZ, cast[int32](winsize))
    if ret < 0:
      # Default to 80 if ioctl fails
      print_int(80)
    if ret >= 0:
      # winsize: rows is first 2 bytes, cols is next 2 bytes
      # Cast to short pointer to read 16-bit values
      var ws_ptr: ptr uint8 = cast[ptr uint8](winsize)
      var cols: int32 = cast[int32](ws_ptr[2]) + (cast[int32](ws_ptr[3]) << 8)
      if cols == 0:
        cols = 80
      print_int(cols)

    print(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 0)

  # lines - get terminal height
  var cmp_lines: int32 = strcmp(capability, cast[ptr uint8]("lines"))
  if cmp_lines == 0:
    var old_brk: int32 = syscall1(SYS_brk, 0)
    var new_brk: int32 = old_brk + 16
    discard syscall1(SYS_brk, new_brk)
    var winsize: ptr int32 = cast[ptr int32](old_brk)

    var ret: int32 = syscall3(SYS_ioctl, STDOUT, TIOCGWINSZ, cast[int32](winsize))
    if ret < 0:
      # Default to 24 if ioctl fails
      print_int(24)
    if ret >= 0:
      # winsize: rows is first 2 bytes
      var ws_ptr: ptr uint8 = cast[ptr uint8](winsize)
      var rows: int32 = cast[int32](ws_ptr[0]) + (cast[int32](ws_ptr[1]) << 8)
      if rows == 0:
        rows = 24
      print_int(rows)

    print(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 0)

  # cup - move cursor
  var cmp_cup: int32 = strcmp(capability, cast[ptr uint8]("cup"))
  if cmp_cup == 0:
    if argc < 4:
      print_err(cast[ptr uint8]("tput cup: missing arguments (Y X)\n"))
      discard syscall1(SYS_exit, 1)

    var y_str: ptr uint8 = get_argv(2)
    var x_str: ptr uint8 = get_argv(3)

    var y: int32 = parse_int(y_str)
    var x: int32 = parse_int(x_str)

    if y < 0:
      print_err(cast[ptr uint8]("tput cup: invalid Y coordinate\n"))
      discard syscall1(SYS_exit, 1)
    if x < 0:
      print_err(cast[ptr uint8]("tput cup: invalid X coordinate\n"))
      discard syscall1(SYS_exit, 1)

    # ANSI escape: ESC[Y;XH (cursor position - 1-indexed)
    print(cast[ptr uint8]("\x1b["))
    print_int(y + 1)
    print(cast[ptr uint8](";"))
    print_int(x + 1)
    print(cast[ptr uint8]("H"))

    discard syscall1(SYS_exit, 0)

  # Unknown capability
  print_err(cast[ptr uint8]("tput: unknown capability '"))
  print_err(capability)
  print_err(cast[ptr uint8]("'\n"))
  discard syscall1(SYS_exit, 1)
