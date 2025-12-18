# fold - wrap lines to specified width
# Usage: fold [-w WIDTH] [FILE]
# Default width: 80 characters
# Part of PoodillionOS text utilities

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
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return cast[int32](s1[i]) - cast[int32](s2[i])
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 0 - cast[int32](s2[i])
  return 0

proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] >= cast[uint8](48):
    if s[i] > cast[uint8](57):
      break
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

proc main() =
  var argc: int32 = get_argc()

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Parse arguments
  var width: int32 = 80
  var input_fd: int32 = STDIN
  var i: int32 = 1

  while i < argc:
    var arg: ptr uint8 = get_argv(i)
    if strcmp(arg, cast[ptr uint8]("-w")) == 0:
      i = i + 1
      if i >= argc:
        print_err(cast[ptr uint8]("fold: -w requires width\n"))
        discard syscall1(SYS_exit, 1)
      var width_arg: ptr uint8 = get_argv(i)
      width = parse_int(width_arg)
      if width <= 0:
        width = 80
    else:
      if arg[0] != cast[uint8](45):  # not a flag
        input_fd = syscall2(SYS_open, cast[int32](arg), O_RDONLY)
        if input_fd < 0:
          print_err(cast[ptr uint8]("fold: cannot open file\n"))
          discard syscall1(SYS_exit, 1)
    i = i + 1

  # Process input
  var col: int32 = 0
  var running: int32 = 1

  while running != 0:
    var n: int32 = syscall3(SYS_read, input_fd, cast[int32](buffer), 4096)
    if n <= 0:
      running = 0
      break

    var j: int32 = 0
    while j < n:
      var ch: uint8 = buffer[j]

      if ch == cast[uint8](10):  # newline
        discard syscall3(SYS_write, STDOUT, cast[int32](addr(ch)), 1)
        col = 0
      else:
        if col >= width:
          discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
          col = 0
        discard syscall3(SYS_write, STDOUT, cast[int32](addr(ch)), 1)
        col = col + 1

      j = j + 1

  if input_fd != STDIN:
    discard syscall1(SYS_close, input_fd)

  discard syscall1(SYS_exit, 0)
