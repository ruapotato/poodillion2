# chmod - Change file permissions
# Usage: chmod MODE FILE
# MODE can be octal (755) or symbolic (u+x, u-w, etc)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_chmod: int32 = 15

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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

# Check if character is octal digit (0-7)
proc is_octal_digit(c: uint8): int32 =
  if c >= cast[uint8](48):
    if c <= cast[uint8](55):
      return 1
  return 0

# Parse octal mode string to integer
proc parse_octal_mode(mode_str: ptr uint8): int32 =
  var mode: int32 = 0
  var i: int32 = 0

  while mode_str[i] != cast[uint8](0):
    var is_oct: int32 = is_octal_digit(mode_str[i])
    if is_oct == 0:
      return -1

    var digit: int32 = cast[int32](mode_str[i]) - 48
    mode = (mode << 3) | digit
    i = i + 1

  return mode

proc main() =
  var argc: int32 = get_argc()
  if argc < 3:
    print_err(cast[ptr uint8]("Usage: chmod MODE FILE\n"))
    print_err(cast[ptr uint8]("  MODE: octal permissions (e.g., 755, 644)\n"))
    discard syscall1(SYS_exit, 1)

  var mode_str: ptr uint8 = get_argv(1)
  var filename: ptr uint8 = get_argv(2)

  # Parse mode (currently only octal supported)
  var mode: int32 = parse_octal_mode(mode_str)

  if mode < 0:
    print_err(cast[ptr uint8]("chmod: invalid mode '"))
    print_err(mode_str)
    print_err(cast[ptr uint8]("'\n"))
    print_err(cast[ptr uint8]("  Use octal format (e.g., 755, 644)\n"))
    discard syscall1(SYS_exit, 1)

  # Call chmod syscall
  var ret: int32 = syscall2(SYS_chmod, cast[int32](filename), mode)

  if ret < 0:
    print_err(cast[ptr uint8]("chmod: cannot change permissions of '"))
    print_err(filename)
    print_err(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
