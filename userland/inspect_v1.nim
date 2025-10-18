# inspect_v1 - just read and print magic, no helper functions
const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc main() =
  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read magic header
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 4)

  # Write "Magic: "
  discard syscall3(SYS_write, STDOUT, cast[int32]("Magic: "), 7)

  # Write the 4 magic bytes
  var i: int32 = 0
  while i < 4:
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(buffer[i])), 1)
    i = i + 1

  # Write newline
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  discard syscall1(SYS_exit, 0)
