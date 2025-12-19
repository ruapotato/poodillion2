# join - join lines of two files on common field
# Usage: join FILE1 FILE2
# Join lines based on first whitespace-separated field

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Compare first field of two lines
proc compare_fields(line1: ptr uint8, len1: int32, line2: ptr uint8, len2: int32): int32 =
  var i: int32 = 0
  var j: int32 = 0

  # Compare until whitespace or end
  while i < len1:
    if j >= len2:
      return 1
    var c1: uint8 = line1[i]
    var c2: uint8 = line2[j]

    # Check for field end
    if c1 == cast[uint8](32):  # space
      if c2 == cast[uint8](32):
        return 0
      if c2 == cast[uint8](9):   # tab
        return 0
      if c2 == cast[uint8](10):  # newline
        return 0
      return -1
    if c1 == cast[uint8](9):   # tab
      if c2 == cast[uint8](32):
        return 0
      if c2 == cast[uint8](9):
        return 0
      if c2 == cast[uint8](10):
        return 0
      return -1
    if c1 == cast[uint8](10):  # newline
      if c2 == cast[uint8](32):
        return -1
      if c2 == cast[uint8](9):
        return -1
      if c2 == cast[uint8](10):
        return 0
      return -1

    if c2 == cast[uint8](32):
      return 1
    if c2 == cast[uint8](9):
      return 1
    if c2 == cast[uint8](10):
      return 1

    if c1 < c2:
      return -1
    if c1 > c2:
      return 1

    i = i + 1
    j = j + 1

  if j < len2:
    var c2: uint8 = line2[j]
    if c2 == cast[uint8](32):
      return 0
    if c2 == cast[uint8](9):
      return 0
    if c2 == cast[uint8](10):
      return 0
    return -1

  return 0

# Read a line from file (returns length, -1 on EOF)
proc read_line(fd: int32, buffer: ptr uint8, buf_ptr: ptr int32, buf_size_ptr: ptr int32, line: ptr uint8, max_len: int32): int32 =
  var pos: int32 = 0
  var done: int32 = 0

  while done == 0:
    if buf_ptr[0] >= buf_size_ptr[0]:
      buf_size_ptr[0] = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
      buf_ptr[0] = 0
      if buf_size_ptr[0] <= 0:
        if pos > 0:
          return pos
        return -1

    if buf_ptr[0] < buf_size_ptr[0]:
      var c: uint8 = buffer[buf_ptr[0]]
      buf_ptr[0] = buf_ptr[0] + 1

      if pos < max_len:
        line[pos] = c
        pos = pos + 1

      if c == cast[uint8](10):  # newline
        done = 1

  return pos

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: join FILE1 FILE2\n"))
    discard syscall1(SYS_exit, 1)

  # Open files
  var file1: ptr uint8 = get_argv(1)
  var file2: ptr uint8 = get_argv(2)

  var fd1: int32 = syscall3(SYS_open, cast[int32](file1), O_RDONLY, 0)
  if fd1 < 0:
    print_err(cast[ptr uint8]("join: cannot open FILE1\n"))
    discard syscall1(SYS_exit, 1)

  var fd2: int32 = syscall3(SYS_open, cast[int32](file2), O_RDONLY, 0)
  if fd2 < 0:
    print_err(cast[ptr uint8]("join: cannot open FILE2\n"))
    discard syscall1(SYS_exit, 1)

  # Allocate buffers
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)

  var buf1: ptr uint8 = cast[ptr uint8](old_brk)
  var buf2: ptr uint8 = cast[ptr uint8](old_brk + 4096)
  var line1: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var line2: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 2048)
  var buf_pos1: ptr int32 = cast[ptr int32](old_brk + 12288)
  var buf_size1: ptr int32 = cast[ptr int32](old_brk + 12292)
  var buf_pos2: ptr int32 = cast[ptr int32](old_brk + 12296)
  var buf_size2: ptr int32 = cast[ptr int32](old_brk + 12300)

  buf_pos1[0] = 0
  buf_size1[0] = 0
  buf_pos2[0] = 0
  buf_size2[0] = 0

  # Read first lines
  var len1: int32 = read_line(fd1, buf1, buf_pos1, buf_size1, line1, 2048)
  var len2: int32 = read_line(fd2, buf2, buf_pos2, buf_size2, line2, 2048)

  # Process files
  while len1 > 0:
    if len2 <= 0:
      break

    var cmp: int32 = compare_fields(line1, len1, line2, len2)

    if cmp == 0:
      # Match! Print joined line
      # Remove trailing newline from line1
      var out_len: int32 = len1
      if line1[len1 - 1] == cast[uint8](10):
        out_len = len1 - 1

      discard syscall3(SYS_write, STDOUT, cast[int32](line1), out_len)
      discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
      discard syscall3(SYS_write, STDOUT, cast[int32](line2), len2)

      # Advance both
      len1 = read_line(fd1, buf1, buf_pos1, buf_size1, line1, 2048)
      len2 = read_line(fd2, buf2, buf_pos2, buf_size2, line2, 2048)
    if cmp < 0:
      # line1 < line2, advance file1
      len1 = read_line(fd1, buf1, buf_pos1, buf_size1, line1, 2048)
    if cmp > 0:
      # line1 > line2, advance file2
      len2 = read_line(fd2, buf2, buf_pos2, buf_size2, line2, 2048)

  discard syscall1(SYS_close, fd1)
  discard syscall1(SYS_close, fd2)
  discard syscall1(SYS_exit, 0)
