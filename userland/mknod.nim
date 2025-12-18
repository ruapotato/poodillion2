# mknod - Create special files
# Usage: mknod name type [major minor]
#   type: p (FIFO), c (character device), b (block device)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_mknod: int32 = 14

const STDOUT: int32 = 1
const STDERR: int32 = 2

# File type bits
const S_IFIFO: int32 = 4096      # 0010000 - FIFO
const S_IFCHR: int32 = 8192      # 0020000 - character device
const S_IFBLK: int32 = 24576     # 0060000 - block device

# Permission bits (0666)
const S_IRUSR: int32 = 256       # 0400
const S_IWUSR: int32 = 128       # 0200
const S_IRGRP: int32 = 32        # 0040
const S_IWGRP: int32 = 16        # 0020
const S_IROTH: int32 = 4         # 0004
const S_IWOTH: int32 = 2         # 0002

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

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: mknod name type [major minor]\n"))
    print_err(cast[ptr uint8]("  type: p (FIFO), c (char device), b (block device)\n"))
    discard syscall1(SYS_exit, 1)

  var name: ptr uint8 = get_argv(1)
  var type_str: ptr uint8 = get_argv(2)
  var type_char: uint8 = type_str[0]

  var mode: int32 = S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH
  var dev: int32 = 0

  # Determine file type
  if type_char == cast[uint8](112):  # 'p' - FIFO
    mode = mode | S_IFIFO
    dev = 0
  else:
    # For 'c' (char) or 'b' (block), we need major and minor numbers
    if argc < 5:
      print_err(cast[ptr uint8]("mknod: device files require major and minor numbers\n"))
      discard syscall1(SYS_exit, 1)

    var major_str: ptr uint8 = get_argv(3)
    var minor_str: ptr uint8 = get_argv(4)
    var major: int32 = atoi(major_str)
    var minor: int32 = atoi(minor_str)

    if major < 0 or minor < 0:
      print_err(cast[ptr uint8]("mknod: invalid major or minor number\n"))
      discard syscall1(SYS_exit, 1)

    # Create device number: (major << 8) | minor
    dev = (major * 256) | minor

    if type_char == cast[uint8](99):  # 'c' - character device
      mode = mode | S_IFCHR
    else:
      if type_char == cast[uint8](98):  # 'b' - block device
        mode = mode | S_IFBLK
      else:
        print_err(cast[ptr uint8]("mknod: invalid type (use p, c, or b)\n"))
        discard syscall1(SYS_exit, 1)

  # Create the special file
  var result: int32 = syscall3(SYS_mknod, cast[int32](name), mode, dev)

  if result < 0:
    print_err(cast[ptr uint8]("mknod: cannot create special file '"))
    print_err(name)
    print_err(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
