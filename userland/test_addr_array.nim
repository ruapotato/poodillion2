# Test addr with array indexing
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const STDOUT: int32 = 1

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc main() =
  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Set some values
  buffer[0] = cast[uint8](65)  # 'A'
  buffer[1] = cast[uint8](66)  # 'B'
  buffer[2] = cast[uint8](67)  # 'C'
  buffer[3] = cast[uint8](68)  # 'D'

  # Write using addr(buffer[i])
  var i: int32 = 0
  while i < 4:
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(buffer[i])), 1)
    i = i + 1

  discard syscall1(SYS_exit, 0)
