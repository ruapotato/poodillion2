# truncate - Shrink or extend file to specified size
# Usage: truncate -s size file

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_truncate: int32 = 92

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

# Simple string to integer conversion
proc atoi(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    var digit: uint8 = s[i]
    if digit >= cast[uint8](48) and digit <= cast[uint8](57):  # '0' to '9'
      result = result * 10 + cast[int32](digit - cast[uint8](48))
    else:
      return 0 - 1  # Error
    i = i + 1
  return result

# Check if two strings match
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while true:
    if s1[i] != s2[i]:
      return 1
    if s1[i] == cast[uint8](0):
      return 0
    i = i + 1
  return 0

proc main() =
  var argc: int32 = get_argc()

  if argc < 4:
    print_err(cast[ptr uint8]("Usage: truncate -s size file\n"))
    discard syscall1(SYS_exit, 1)

  # Parse arguments: expect -s flag
  var size_flag: ptr uint8 = get_argv(1)
  if strcmp(size_flag, cast[ptr uint8]("-s")) != 0:
    print_err(cast[ptr uint8]("truncate: -s option required\n"))
    print_err(cast[ptr uint8]("Usage: truncate -s size file\n"))
    discard syscall1(SYS_exit, 1)

  var size_str: ptr uint8 = get_argv(2)
  var filename: ptr uint8 = get_argv(3)

  # Parse size
  var size: int32 = atoi(size_str)
  if size < 0:
    print_err(cast[ptr uint8]("truncate: invalid size\n"))
    discard syscall1(SYS_exit, 1)

  # Truncate the file
  var result: int32 = syscall2(SYS_truncate, cast[int32](filename), size)

  if result < 0:
    print_err(cast[ptr uint8]("truncate: cannot truncate '"))
    print_err(filename)
    print_err(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
