# tty - Print terminal name
# Usage: tty
# Reads from /proc/self/fd/0 (symlink to tty)
# Uses SYS_readlink (85)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_readlink: int32 = 85

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build path: /proc/self/fd/0
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](115)  # s
  path[7] = cast[uint8](101)  # e
  path[8] = cast[uint8](108)  # l
  path[9] = cast[uint8](102)  # f
  path[10] = cast[uint8](47)  # /
  path[11] = cast[uint8](102) # f
  path[12] = cast[uint8](100) # d
  path[13] = cast[uint8](47)  # /
  path[14] = cast[uint8](48)  # 0
  path[15] = cast[uint8](0)

  # Read symbolic link
  var ret: int32 = syscall3(SYS_readlink, cast[int32](path), cast[int32](buf), 4000)

  if ret < 0:
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)

  # Check if it's a tty (starts with /dev/pts or /dev/tty)
  # /dev/pts = 47 100 101 118 47 112 116 115
  # /dev/tty = 47 100 101 118 47 116 116 121
  if ret < 8:
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)

  # Check for /dev/
  if buf[0] != cast[uint8](47):   # /
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)
  if buf[1] != cast[uint8](100):  # d
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)
  if buf[2] != cast[uint8](101):  # e
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)
  if buf[3] != cast[uint8](118):  # v
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)
  if buf[4] != cast[uint8](47):   # /
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)

  # Check for pts or tty
  var is_tty: int32 = 0

  # Check for "pts"
  if ret >= 8:
    if buf[5] == cast[uint8](112):  # p
      if buf[6] == cast[uint8](116):  # t
        if buf[7] == cast[uint8](115):  # s
          is_tty = 1

  # Check for "tty"
  if ret >= 8:
    if buf[5] == cast[uint8](116):  # t
      if buf[6] == cast[uint8](116):  # t
        if buf[7] == cast[uint8](121):  # y
          is_tty = 1

  if is_tty == 0:
    print(cast[ptr uint8]("not a tty\n"))
    discard syscall1(SYS_exit, 1)

  # Print the full path
  discard syscall3(SYS_write, STDOUT, cast[int32](buf), ret)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  discard syscall1(SYS_exit, 0)
