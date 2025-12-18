# mv - move/rename file or directory
# Usage: mv source destination

const SYS_rename: int32 = 38
const SYS_write: int32 = 4
const SYS_exit: int32 = 1

const STDOUT: int32 = 1
const STDERR: int32 = 2

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

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: mv source destination\n"))
    discard syscall1(SYS_exit, 1)

  var source: ptr uint8 = get_argv(1)
  var dest: ptr uint8 = get_argv(2)

  var result: int32 = syscall2(SYS_rename, cast[int32](source), cast[int32](dest))

  if result < 0:
    print_err(cast[ptr uint8]("mv: cannot move/rename file\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
