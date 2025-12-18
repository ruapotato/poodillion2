# readlink - Print value of a symbolic link
# Usage: readlink path

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_readlink: int32 = 85

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

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

proc main() =
  var argc: int32 = get_argc()
  if argc < 2:
    print_err(cast[ptr uint8]("Usage: readlink path\n"))
    discard syscall1(SYS_exit, 1)

  var path: ptr uint8 = get_argv(1)

  # Allocate buffer for result
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  # Read symbolic link
  var ret: int32 = syscall3(SYS_readlink, cast[int32](path), cast[int32](buf), 4096)
  if ret < 0:
    print_err(cast[ptr uint8]("readlink: "))
    print_err(path)
    print_err(cast[ptr uint8](": Not a symbolic link or cannot read\n"))
    discard syscall1(SYS_exit, 1)

  # Print result (readlink does not null-terminate)
  discard syscall3(SYS_write, STDOUT, cast[int32](buf), ret)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  discard syscall1(SYS_exit, 0)
