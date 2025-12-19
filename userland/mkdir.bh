# mkdir - create directory
# Usage: mkdir dirname

const SYS_mkdir: int32 = 39
const SYS_write: int32 = 4
const SYS_exit: int32 = 1

const STDOUT: int32 = 1
const STDERR: int32 = 2

# Directory permissions: 0755 (rwxr-xr-x)
const S_IRWXU: int32 = 448   # 0700 - user rwx
const S_IRGRP: int32 = 32    # 0040 - group r
const S_IXGRP: int32 = 8     # 0010 - group x
const S_IROTH: int32 = 4     # 0004 - others r
const S_IXOTH: int32 = 1     # 0001 - others x

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

  if argc < 2:
    print_err(cast[ptr uint8]("Usage: mkdir dirname\n"))
    discard syscall1(SYS_exit, 1)

  var dirname: ptr uint8 = get_argv(1)

  # Create directory with mode 0755
  var mode: int32 = S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH
  var result: int32 = syscall2(SYS_mkdir, cast[int32](dirname), mode)

  if result < 0:
    print_err(cast[ptr uint8]("mkdir: cannot create directory\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
