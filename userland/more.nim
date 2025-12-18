# more - simple pager (display one screenful at a time)
# Usage: more [FILE]
# Space = next page, Enter = next line, q = quit

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_ioctl: int32 = 54

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

# Terminal control (ioctl)
const TCGETS: int32 = 0x5401
const TCSETS: int32 = 0x5402
const ICANON: int32 = 2
const ECHO: int32 = 8

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc main() =
  var argc: int32 = get_argc()
  var fd: int32 = STDIN

  # Open file if provided
  if argc >= 2:
    var filename: ptr uint8 = get_argv(1)
    fd = syscall3(SYS_open, cast[int32](filename), O_RDONLY, 0)
    if fd < 0:
      print_err(cast[ptr uint8]("more: cannot open file\n"))
      discard syscall1(SYS_exit, 1)

  # Allocate buffers
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var line_buffer: ptr uint8 = cast[ptr uint8](old_brk + 4096)

  # Save terminal settings (for stdin)
  var termios_old: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 1024)
  var termios_new: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 1024 + 64)

  # Get current terminal settings
  discard syscall3(SYS_ioctl, STDIN, TCGETS, cast[int32](termios_old))

  # Copy to new settings
  var k: int32 = 0
  while k < 64:
    termios_new[k] = termios_old[k]
    k = k + 1

  # Disable canonical mode and echo (raw mode)
  var lflag_ptr: ptr int32 = cast[ptr int32](termios_new + 12)
  var lflag: int32 = lflag_ptr[0]
  lflag = lflag - (lflag % (ICANON * 2) - lflag % ICANON)  # Clear ICANON
  lflag = lflag - (lflag % (ECHO * 2) - lflag % ECHO)      # Clear ECHO
  lflag_ptr[0] = lflag

  # Set raw mode
  discard syscall3(SYS_ioctl, STDIN, TCSETS, cast[int32](termios_new))

  var line_count: int32 = 0
  var buf_pos: int32 = 0
  var buf_size: int32 = 0
  var running: int32 = 1
  var line_start: int32 = 0

  while running != 0:
    # Display lines
    while line_count < 24:
      # Build a line
      line_start = 0
      var line_done: int32 = 0

      while line_done == 0:
        # Need more data?
        if buf_pos >= buf_size:
          buf_size = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
          buf_pos = 0
          if buf_size <= 0:
            running = 0
            line_done = 1
            break

        if buf_pos < buf_size:
          var c: uint8 = buffer[buf_pos]
          buf_pos = buf_pos + 1

          line_buffer[line_start] = c
          line_start = line_start + 1

          if c == cast[uint8](10):  # newline
            line_done = 1

      # Display the line
      if line_start > 0:
        discard syscall3(SYS_write, STDOUT, cast[int32](line_buffer), line_start)
        line_count = line_count + 1

      if running == 0:
        break

    # Check if we're done
    if running == 0:
      break

    # Show prompt
    print(cast[ptr uint8]("--More--"))

    # Wait for key
    var key_buf: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 1024 + 128)
    var key_read: int32 = syscall3(SYS_read, STDIN, cast[int32](key_buf), 1)

    # Clear prompt
    print(cast[ptr uint8]("\r        \r"))

    if key_read <= 0:
      running = 0
      break

    var key: uint8 = key_buf[0]

    # q = quit
    if key == cast[uint8](113):  # 'q'
      running = 0

    # Enter = one more line
    if key == cast[uint8](10):   # '\n'
      line_count = 23

    # Space = next page
    if key == cast[uint8](32):   # ' '
      line_count = 0

  # Restore terminal settings
  discard syscall3(SYS_ioctl, STDIN, TCSETS, cast[int32](termios_old))

  # Close file if opened
  if fd != STDIN:
    discard syscall1(SYS_close, fd)

  discard syscall1(SYS_exit, 0)
