# paste - merge lines of files
# Usage: paste FILE1 FILE2
#        paste -d DELIM FILE1 FILE2
# Combine corresponding lines with tab separator (or custom delimiter)

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
  var delim: uint8 = cast[uint8](9)  # tab
  var arg_idx: int32 = 1

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: paste [-d DELIM] FILE1 FILE2\n"))
    discard syscall1(SYS_exit, 1)

  # Parse -d option
  if argc >= 4:
    var arg: ptr uint8 = get_argv(1)
    if arg[0] == cast[uint8](45):  # '-'
      if arg[1] == cast[uint8](100):  # 'd'
        var delim_arg: ptr uint8 = get_argv(2)
        delim = delim_arg[0]
        arg_idx = 3

  if argc <= arg_idx:
    print_err(cast[ptr uint8]("paste: not enough files\n"))
    discard syscall1(SYS_exit, 1)

  # Open files
  var file1: ptr uint8 = get_argv(arg_idx)
  var file2: ptr uint8 = get_argv(arg_idx + 1)

  var fd1: int32 = syscall3(SYS_open, cast[int32](file1), O_RDONLY, 0)
  if fd1 < 0:
    print_err(cast[ptr uint8]("paste: cannot open FILE1\n"))
    discard syscall1(SYS_exit, 1)

  var fd2: int32 = syscall3(SYS_open, cast[int32](file2), O_RDONLY, 0)
  if fd2 < 0:
    print_err(cast[ptr uint8]("paste: cannot open FILE2\n"))
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

  # Process files line by line
  var running: int32 = 1
  while running != 0:
    var len1: int32 = read_line(fd1, buf1, buf_pos1, buf_size1, line1, 2048)
    var len2: int32 = read_line(fd2, buf2, buf_pos2, buf_size2, line2, 2048)

    if len1 <= 0:
      if len2 <= 0:
        running = 0
        break

    # Print line1 (without trailing newline)
    if len1 > 0:
      var out_len: int32 = len1
      if line1[len1 - 1] == cast[uint8](10):
        out_len = len1 - 1
      discard syscall3(SYS_write, STDOUT, cast[int32](line1), out_len)

    # Print delimiter
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(delim)), 1)

    # Print line2
    if len2 > 0:
      discard syscall3(SYS_write, STDOUT, cast[int32](line2), len2)
    if len2 <= 0:
      discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  discard syscall1(SYS_close, fd1)
  discard syscall1(SYS_close, fd2)
  discard syscall1(SYS_exit, 0)
