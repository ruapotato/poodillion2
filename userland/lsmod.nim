# lsmod - List loaded kernel modules
# Reads /proc/modules and formats output
# Format: Module Size Used_by
# Part of PoodillionOS kernel utilities

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2
const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_error(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 65536  # 64KB buffer
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build path: /proc/modules
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](109)  # m
  path[7] = cast[uint8](111)  # o
  path[8] = cast[uint8](100)  # d
  path[9] = cast[uint8](117)  # u
  path[10] = cast[uint8](108) # l
  path[11] = cast[uint8](101) # e
  path[12] = cast[uint8](115) # s
  path[13] = cast[uint8](0)

  # Open /proc/modules
  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print_error(cast[ptr uint8]("lsmod: cannot open /proc/modules\n"))
    discard syscall1(SYS_exit, 1)

  # Print header
  print(cast[ptr uint8]("Module                  Size  Used by\n"))

  # Read and print module list
  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 65536 - 256)
  discard syscall1(SYS_close, fd)

  if nread < 0:
    print_error(cast[ptr uint8]("lsmod: cannot read /proc/modules\n"))
    discard syscall1(SYS_exit, 1)

  if nread == 0:
    # No modules loaded
    discard syscall1(SYS_exit, 0)

  # Print the raw output from /proc/modules
  # Format is already: module_name size refcount [used_by_list] status load_address
  # We'll just print the first three fields for simplicity

  var i: int32 = 0
  var line_start: int32 = 0
  var field: int32 = 0
  var space_count: int32 = 0

  while i < nread:
    var ch: uint8 = buffer[i]

    if ch == cast[uint8](10):  # newline
      # End of line - add newline
      buffer[i] = cast[uint8](10)
      discard syscall3(SYS_write, STDOUT, cast[int32](buffer) + line_start, i - line_start + 1)
      line_start = i + 1
      field = 0
      space_count = 0

    i = i + 1

  # Print any remaining data
  if line_start < nread:
    if buffer[nread - 1] != cast[uint8](10):
      buffer[nread] = cast[uint8](10)
      nread = nread + 1
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer) + line_start, nread - line_start)

  discard syscall1(SYS_exit, 0)
