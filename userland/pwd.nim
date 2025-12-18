# pwd - Print working directory
# Uses SYS_getcwd (183) to get current working directory

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getcwd: int32 = 183

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

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

proc main() =
  # Allocate buffer for path (4KB should be plenty)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk)

  # Call getcwd
  var ret: int32 = syscall2(SYS_getcwd, cast[int32](path_buf), 4096)

  if ret < 0:
    print_err(cast[ptr uint8]("pwd: cannot get current directory\n"))
    discard syscall1(SYS_exit, 1)

  # Print the path
  print(path_buf)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  discard syscall1(SYS_exit, 0)
