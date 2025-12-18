# chgrp - Change file group
# Usage: chgrp GID FILE
# Uses numeric GID, keeps UID unchanged (-1)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_chown: int32 = 182

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

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

# Check if character is digit
proc is_digit(c: uint8): int32 =
  if c >= cast[uint8](48):
    if c <= cast[uint8](57):
      return 1
  return 0

# Parse integer from string
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0

  while s[i] != cast[uint8](0):
    var is_dig: int32 = is_digit(s[i])
    if is_dig == 0:
      return -1

    var digit: int32 = cast[int32](s[i]) - 48
    result = result * 10 + digit
    i = i + 1

  return result

proc main() =
  var argc: int32 = get_argc()
  if argc < 3:
    print_err(cast[ptr uint8]("Usage: chgrp GID FILE\n"))
    print_err(cast[ptr uint8]("  Example: chgrp 1000 myfile.txt\n"))
    discard syscall1(SYS_exit, 1)

  var gid_str: ptr uint8 = get_argv(1)
  var filename: ptr uint8 = get_argv(2)

  # Parse GID
  var gid: int32 = parse_int(gid_str)

  if gid < 0:
    print_err(cast[ptr uint8]("chgrp: invalid GID '"))
    print_err(gid_str)
    print_err(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  # Call chown syscall with uid=-1 to keep UID unchanged
  var uid: int32 = -1
  var ret: int32 = syscall3(SYS_chown, cast[int32](filename), uid, gid)

  if ret < 0:
    print_err(cast[ptr uint8]("chgrp: cannot change group of '"))
    print_err(filename)
    print_err(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
