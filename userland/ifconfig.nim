# ifconfig - Display network interface configuration
# Reads from /proc/net/dev and shows interface names

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

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)

  var dev_path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build /proc/net/dev path
  dev_path[0] = cast[uint8](47)   # /
  dev_path[1] = cast[uint8](112)  # p
  dev_path[2] = cast[uint8](114)  # r
  dev_path[3] = cast[uint8](111)  # o
  dev_path[4] = cast[uint8](99)   # c
  dev_path[5] = cast[uint8](47)   # /
  dev_path[6] = cast[uint8](110)  # n
  dev_path[7] = cast[uint8](101)  # e
  dev_path[8] = cast[uint8](116)  # t
  dev_path[9] = cast[uint8](47)   # /
  dev_path[10] = cast[uint8](100) # d
  dev_path[11] = cast[uint8](101) # e
  dev_path[12] = cast[uint8](118) # v
  dev_path[13] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](dev_path), O_RDONLY, 0)
  if fd < 0:
    print(cast[ptr uint8]("ifconfig: cannot open /proc/net/dev\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print(cast[ptr uint8]("ifconfig: cannot read /proc/net/dev\n"))
    discard syscall1(SYS_exit, 1)

  # Parse /proc/net/dev line by line
  var i: int32 = 0
  var line_num: int32 = 0
  var line_start: int32 = 0

  while i < nread:
    if buffer[i] == cast[uint8](10):
      line_num = line_num + 1

      # Skip first 2 lines (headers)
      if line_num > 2:
        # Extract interface name from this line
        var j: int32 = line_start

        # Skip spaces at start of line
        var skip_done: int32 = 0
        while j < i:
          if skip_done == 0:
            if buffer[j] == cast[uint8](32):
              j = j + 1
            if j < i:
              if buffer[j] != cast[uint8](32):
                skip_done = 1
          if skip_done == 1:
            j = i

        # Now j points to first non-space character
        # Print characters until we hit a colon
        var print_done: int32 = 0
        while j < i:
          if print_done == 0:
            if buffer[j] == cast[uint8](58):
              print_done = 1
              print(cast[ptr uint8]("\n"))
            if print_done == 0:
              discard syscall3(SYS_write, STDOUT, cast[int32](cast[ptr uint8](cast[int32](buffer) + j)), 1)
              j = j + 1
          if print_done == 1:
            j = i

      line_start = i + 1

    i = i + 1

  discard syscall1(SYS_exit, 0)
