# Test getdents64 syscall

const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getdents64: int32 = 220

const STDOUT: int32 = 1
const O_RDONLY: int32 = 0
const O_DIRECTORY: int32 = 65536

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

proc print_num(n: int32) =
  var buf: ptr uint8 = cast[ptr uint8](0)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  buf = cast[ptr uint8](old_brk)

  var num: int32 = n
  if num < 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("-"), 1)
    num = 0 - num

  var i: int32 = 0
  if num == 0:
    buf[0] = cast[uint8](48)
    i = 1
  else:
    while num > 0:
      var digit: int32 = num % 10
      buf[i] = cast[uint8](48 + digit)
      num = num / 10
      i = i + 1

  # Reverse
  var j: int32 = 0
  var k: int32 = i - 1
  while j < k:
    var temp: uint8 = buf[j]
    buf[j] = buf[k]
    buf[k] = temp
    j = j + 1
    k = k - 1

  discard syscall3(SYS_write, STDOUT, cast[int32](buf), i)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Get directory path
  var argc: int32 = get_argc()
  var path: ptr uint8 = cast[ptr uint8](".")
  if argc > 1:
    path = get_argv(1)

  print(cast[ptr uint8]("Opening: "))
  print(path)
  print(cast[ptr uint8]("\n"))

  # Open directory
  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY | O_DIRECTORY, 0)
  print(cast[ptr uint8]("open() returned: "))
  print_num(fd)
  print(cast[ptr uint8]("\n"))

  if fd < 0:
    print(cast[ptr uint8]("Failed to open directory\n"))
    discard syscall1(SYS_exit, 1)

  # Read directory entries
  var nread: int32 = syscall3(SYS_getdents64, fd, cast[int32](buffer), 8192)
  print(cast[ptr uint8]("getdents64() returned: "))
  print_num(nread)
  print(cast[ptr uint8]("\n"))

  if nread > 0:
    var pos: int32 = 0
    while pos < nread:
      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](buffer) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](buffer) + pos + 19)
      var d_type: ptr uint8 = cast[ptr uint8](cast[int32](buffer) + pos + 18)

      print(cast[ptr uint8]("  "))
      print(d_name)
      print(cast[ptr uint8](" (type="))
      print_num(cast[int32](d_type[0]))
      print(cast[ptr uint8](")\n"))

      pos = pos + reclen

  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)
