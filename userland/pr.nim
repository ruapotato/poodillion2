# pr - Paginate files for printing
# Usage: pr [FILE]
#        pr -h "HEADER" [FILE]
# Format with header (date, filename, page number)
# 66 lines per page, with header/footer margins

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_time: int32 = 13

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

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

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  var num: int32 = n
  var i: int32 = 0

  while num > 0:
    var digit: int32 = num % 10
    buffer[i] = cast[uint8](48 + digit)
    num = num / 10
    i = i + 1

  # Print in reverse
  var j: int32 = i - 1
  while j >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer + j), 1)
    j = j - 1

# Simple date string (just placeholder)
proc get_date_str(buf: ptr uint8) =
  # For simplicity, just use a fixed format
  var date: ptr uint8 = cast[ptr uint8]("2025-01-01 00:00")
  var i: int32 = 0
  while date[i] != cast[uint8](0):
    buf[i] = date[i]
    i = i + 1
  buf[i] = cast[uint8](0)

# Print spaces
proc print_spaces(n: int32) =
  var i: int32 = 0
  while i < n:
    discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
    i = i + 1

# Print header: DATE   FILENAME   Page N
proc print_header(filename: ptr uint8, page: int32, custom_header: ptr uint8) =
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  if custom_header != cast[ptr uint8](0):
    print(custom_header)
    print_spaces(30)
  else:
    # Print date
    var old_brk: int32 = syscall1(SYS_brk, 0)
    var new_brk: int32 = old_brk + 64
    discard syscall1(SYS_brk, new_brk)
    var date_buf: ptr uint8 = cast[ptr uint8](old_brk)
    get_date_str(date_buf)
    print(date_buf)
    print_spaces(5)

    # Print filename
    if filename != cast[ptr uint8](0):
      print(filename)
    else:
      print(cast[ptr uint8]("stdin"))
    print_spaces(5)

  # Print page number
  print(cast[ptr uint8]("Page "))
  print_int(page)

  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

# Print footer (blank lines)
proc print_footer() =
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

proc main() =
  var argc: int32 = get_argc()
  var fd: int32 = STDIN
  var filename: ptr uint8 = cast[ptr uint8](0)
  var custom_header: ptr uint8 = cast[ptr uint8](0)

  # Parse arguments
  var i: int32 = 1
  while i < argc:
    var arg: ptr uint8 = get_argv(i)

    if arg[0] == cast[uint8](45):  # '-'
      if arg[1] == cast[uint8](104):  # 'h'
        # Custom header
        i = i + 1
        if i < argc:
          custom_header = get_argv(i)
    else:
      filename = arg

    i = i + 1

  # Open file if provided
  if filename != cast[ptr uint8](0):
    fd = syscall2(SYS_open, cast[int32](filename), O_RDONLY)
    if fd < 0:
      print_err(cast[ptr uint8]("pr: cannot open file\n"))
      discard syscall1(SYS_exit, 1)

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var line_buf: ptr uint8 = cast[ptr uint8](old_brk + 4096)

  var page: int32 = 1
  var line_on_page: int32 = 0
  var lines_per_page: int32 = 56  # 66 total - 5 header - 5 footer
  var in_line: int32 = 0
  var line_pos: int32 = 0

  # Print first header
  print_header(filename, page, custom_header)

  var running: int32 = 1
  while running != 0:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
    if n <= 0:
      # Flush last line if any
      if line_pos > 0:
        discard syscall3(SYS_write, STDOUT, cast[int32](line_buf), line_pos)
        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
        line_on_page = line_on_page + 1

      running = 0
      break

    var i: int32 = 0
    while i < n:
      var c: uint8 = buffer[i]

      if c == cast[uint8](10):  # newline
        # Output line
        discard syscall3(SYS_write, STDOUT, cast[int32](line_buf), line_pos)
        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
        line_pos = 0
        line_on_page = line_on_page + 1

        # Check if we need a new page
        if line_on_page >= lines_per_page:
          print_footer()
          page = page + 1
          print_header(filename, page, custom_header)
          line_on_page = 0

      else:
        # Add to line buffer
        if line_pos < 4095:
          line_buf[line_pos] = c
          line_pos = line_pos + 1

      i = i + 1

  # Print final footer
  print_footer()

  if fd != STDIN:
    discard syscall1(SYS_close, fd)

  discard syscall1(SYS_exit, 0)
