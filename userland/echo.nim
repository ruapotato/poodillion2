# echo - display a line of text
# Part of PoodillionOS coreutils

# TODO: Import syscalls library
# For now, use extern declarations directly

# Linux syscall numbers
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const STDOUT: int32 = 1

# Syscall wrappers
extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# Helper: string length
proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

# Helper: write to stdout
proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc println(msg: ptr uint8) =
  print(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

# Main program
proc main() =
  # For now, just echo a fixed message
  # TODO: Add argc/argv support for real command-line arguments
  println(cast[ptr uint8]("Hello from Mini-Nim echo!"))
  discard syscall1(SYS_exit, 0)
