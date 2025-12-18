# sync - Sync filesystem buffers to disk
# Usage: sync
# Ensures all cached filesystem changes are written to disk

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_sync: int32 = 36

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print(msg: ptr uint8) =
  # Calculate length
  var len: int32 = 0
  while msg[len] != cast[uint8](0):
    len = len + 1
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc main() =
  # Call sync syscall - no arguments needed
  discard syscall1(SYS_sync, 0)

  print(cast[ptr uint8]("sync: filesystem buffers synchronized\n"))

  discard syscall1(SYS_exit, 0)
