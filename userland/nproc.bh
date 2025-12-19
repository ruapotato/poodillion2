# nproc - Print number of CPUs
# Usage: nproc
# Reads /proc/cpuinfo and counts "processor" lines

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
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

proc print_err(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDERR, cast[int32](s), len)

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n

  # Count digits
  var temp: int32 = num
  var digits: int32 = 0
  while temp > 0:
    digits = digits + 1
    temp = temp / 10

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var pos: int32 = digits
  buf[pos] = cast[uint8](0)
  pos = pos - 1

  temp = num
  while temp > 0:
    var digit: int32 = temp % 10
    buf[pos] = cast[uint8](48 + digit)
    pos = pos - 1
    temp = temp / 10

  print(buf)

# Check if line starts with "processor"
proc starts_with_processor(buf: ptr uint8, start: int32): int32 =
  # "processor" = 112 114 111 99 101 115 115 111 114
  if buf[start] != cast[uint8](112):  # p
    return 0
  if buf[start + 1] != cast[uint8](114):  # r
    return 0
  if buf[start + 2] != cast[uint8](111):  # o
    return 0
  if buf[start + 3] != cast[uint8](99):  # c
    return 0
  if buf[start + 4] != cast[uint8](101):  # e
    return 0
  if buf[start + 5] != cast[uint8](115):  # s
    return 0
  if buf[start + 6] != cast[uint8](115):  # s
    return 0
  if buf[start + 7] != cast[uint8](111):  # o
    return 0
  if buf[start + 8] != cast[uint8](114):  # r
    return 0
  return 1

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32768  # 32KB for cpuinfo
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build path: /proc/cpuinfo
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](99)   # c
  path[7] = cast[uint8](112)  # p
  path[8] = cast[uint8](117)  # u
  path[9] = cast[uint8](105)  # i
  path[10] = cast[uint8](110) # n
  path[11] = cast[uint8](102) # f
  path[12] = cast[uint8](111) # o
  path[13] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("nproc: cannot open /proc/cpuinfo\n"))
    discard syscall1(SYS_exit, 1)

  # Read cpuinfo
  var total_read: int32 = 0
  while 1 == 1:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buf) + total_read, 32000 - total_read)
    if n <= 0:
      break
    total_read = total_read + n

  discard syscall1(SYS_close, fd)

  # Count "processor" lines
  var count: int32 = 0
  var i: int32 = 0
  var line_start: int32 = 0

  while i < total_read:
    if buf[i] == cast[uint8](10):  # newline
      # Check if line starts with "processor"
      if i - line_start >= 9:
        if starts_with_processor(buf, line_start) == 1:
          count = count + 1
      line_start = i + 1
    i = i + 1

  # Check last line
  if line_start < total_read:
    if total_read - line_start >= 9:
      if starts_with_processor(buf, line_start) == 1:
        count = count + 1

  # Print count
  if count == 0:
    count = 1  # At least 1 CPU

  print_int(count)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
