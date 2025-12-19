# mesg - Control message receiving on terminal
# Usage: mesg [y|n]
#   mesg     - Show current state
#   mesg y   - Allow messages (make tty writable by group)
#   mesg n   - Deny messages (make tty not writable by group)
# Uses SYS_fstat and SYS_chmod on /dev/tty

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_fstat: int32 = 108
const SYS_chmod: int32 = 15
const SYS_readlink: int32 = 85

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDWR: int32 = 2

# File mode bits
const S_IWGRP: int32 = 0x0010  # Group write permission

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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

proc main() =
  # Allocate memory for stat buffer and tty path
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)

  var tty_path: ptr uint8 = cast[ptr uint8](old_brk)
  var link_path: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var statbuf: ptr int32 = cast[ptr int32](old_brk + 512)

  # Build /proc/self/fd/0 path
  link_path[0] = cast[uint8](47)   # /
  link_path[1] = cast[uint8](112)  # p
  link_path[2] = cast[uint8](114)  # r
  link_path[3] = cast[uint8](111)  # o
  link_path[4] = cast[uint8](99)   # c
  link_path[5] = cast[uint8](47)   # /
  link_path[6] = cast[uint8](115)  # s
  link_path[7] = cast[uint8](101)  # e
  link_path[8] = cast[uint8](108)  # l
  link_path[9] = cast[uint8](102)  # f
  link_path[10] = cast[uint8](47)  # /
  link_path[11] = cast[uint8](102) # f
  link_path[12] = cast[uint8](100) # d
  link_path[13] = cast[uint8](47)  # /
  link_path[14] = cast[uint8](48)  # 0
  link_path[15] = cast[uint8](0)

  # Read tty path
  var ret: int32 = syscall3(SYS_readlink, cast[int32](link_path), cast[int32](tty_path), 255)
  if ret < 0:
    print_err(cast[ptr uint8]("mesg: not a tty\n"))
    discard syscall1(SYS_exit, 2)

  # Null-terminate tty path
  tty_path[ret] = cast[uint8](0)

  # Open tty device
  var fd: int32 = syscall2(SYS_open, cast[int32](tty_path), O_RDWR)
  if fd < 0:
    print_err(cast[ptr uint8]("mesg: cannot open tty\n"))
    discard syscall1(SYS_exit, 2)

  # Get file stats
  ret = syscall2(SYS_fstat, fd, cast[int32](statbuf))
  if ret < 0:
    print_err(cast[ptr uint8]("mesg: cannot stat tty\n"))
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 2)

  # stat struct: st_mode is at offset 16 (4 + 8 + 4)
  var mode_ptr: ptr uint8 = cast[ptr uint8](statbuf)
  var b0: int32 = cast[int32](mode_ptr[16])
  var b1: int32 = cast[int32](mode_ptr[17]) << 8
  var b2: int32 = cast[int32](mode_ptr[18]) << 16
  var b3: int32 = cast[int32](mode_ptr[19]) << 24
  var mode: int32 = b0 + b1 + b2 + b3

  var argc: int32 = get_argc()

  # No arguments - show current state
  if argc == 1:
    var has_write: int32 = mode & S_IWGRP
    if has_write != 0:
      print(cast[ptr uint8]("is y\n"))
      discard syscall1(SYS_close, fd)
      discard syscall1(SYS_exit, 0)
    if has_write == 0:
      print(cast[ptr uint8]("is n\n"))
      discard syscall1(SYS_close, fd)
      discard syscall1(SYS_exit, 1)

  var arg: ptr uint8 = get_argv(1)

  # mesg y - enable messages
  var cmp_y: int32 = strcmp(arg, cast[ptr uint8]("y"))
  if cmp_y == 0:
    var new_mode: int32 = mode | S_IWGRP
    ret = syscall2(SYS_chmod, cast[int32](tty_path), new_mode)
    if ret < 0:
      print_err(cast[ptr uint8]("mesg: cannot change tty mode\n"))
      discard syscall1(SYS_close, fd)
      discard syscall1(SYS_exit, 2)
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 0)

  # mesg n - disable messages
  var cmp_n: int32 = strcmp(arg, cast[ptr uint8]("n"))
  if cmp_n == 0:
    var new_mode: int32 = mode & (S_IWGRP ^ -1)
    ret = syscall2(SYS_chmod, cast[int32](tty_path), new_mode)
    if ret < 0:
      print_err(cast[ptr uint8]("mesg: cannot change tty mode\n"))
      discard syscall1(SYS_close, fd)
      discard syscall1(SYS_exit, 2)
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 0)

  # Invalid argument
  print_err(cast[ptr uint8]("Usage: mesg [y|n]\n"))
  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 2)
