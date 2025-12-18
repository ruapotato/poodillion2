# touch - create empty file or update timestamp
# Usage: touch filename

const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_write: int32 = 4
const SYS_exit: int32 = 1

const STDOUT: int32 = 1
const STDERR: int32 = 2

# File open flags
const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_TRUNC: int32 = 512

# File permissions: 0644 (rw-r--r--)
const S_IRUSR: int32 = 256   # 0400 - user r
const S_IWUSR: int32 = 128   # 0200 - user w
const S_IRGRP: int32 = 32    # 0040 - group r
const S_IROTH: int32 = 4     # 0004 - others r

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
    print_err(cast[ptr uint8]("Usage: touch filename\n"))
    discard syscall1(SYS_exit, 1)

  var filename: ptr uint8 = get_argv(1)

  # Create file with mode 0644 (rw-r--r--)
  # O_CREAT will create if doesn't exist, otherwise just open it
  var mode: int32 = S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH
  var fd: int32 = syscall3(SYS_open, cast[int32](filename), O_WRONLY | O_CREAT, mode)

  if fd < 0:
    print_err(cast[ptr uint8]("touch: cannot create file\n"))
    discard syscall1(SYS_exit, 1)

  # Close the file
  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)
