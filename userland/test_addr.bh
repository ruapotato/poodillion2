# Test addr operator
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const STDOUT: int32 = 1

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc main() =
  var data: int32 = 0x41424344

  # Write 4 bytes using addr
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(data)), 4)

  discard syscall1(SYS_exit, 0)
