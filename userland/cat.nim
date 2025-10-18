# cat - concatenate files and print on stdout
# Part of PoodillionOS coreutils

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# Global buffer (will be in BSS section)
# Note: Mini-Nim doesn't support arrays yet, so we'll use brk syscall to allocate
# For now, let's use a stack buffer approach

proc main() =
  # Simple cat - read from stdin and write to stdout
  # We'll use brk syscall (SYS_brk = 45) to allocate memory

  const SYS_brk: int32 = 45

  # Get current brk
  var old_brk: int32 = syscall1(SYS_brk, 0)

  # Allocate 4096 bytes
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)

  var buffer_ptr: ptr uint8 = cast[ptr uint8](old_brk)
  var running: int32 = 1

  while running != 0:
    var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer_ptr), 4096)
    if n > 0:
      discard syscall3(SYS_write, STDOUT, cast[int32](buffer_ptr), n)
    if n <= 0:
      running = 0

  discard syscall1(SYS_exit, 0)
