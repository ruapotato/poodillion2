# uptime - Show how long the system has been running
# Parses /proc/uptime to get system uptime in seconds

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

# Parse integer from string
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  # Skip leading whitespace
  while s[i] == cast[uint8](32):
    i = i + 1
  # Parse digits
  while s[i] >= cast[uint8](48):
    if s[i] <= cast[uint8](57):
      result = result * 10 + cast[int32](s[i]) - 48
      i = i + 1
    else:
      break
  return result

# Print integer with leading zero if needed
proc print_int_pad(n: int32) =
  if n < 10:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)

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

# Print integer without padding
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

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build path: /proc/uptime
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](117)  # u
  path[7] = cast[uint8](112)  # p
  path[8] = cast[uint8](116)  # t
  path[9] = cast[uint8](105)  # i
  path[10] = cast[uint8](109) # m
  path[11] = cast[uint8](101) # e
  path[12] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print(cast[ptr uint8]("uptime: cannot open /proc/uptime\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 256)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print(cast[ptr uint8]("uptime: cannot read /proc/uptime\n"))
    discard syscall1(SYS_exit, 1)

  buffer[nread] = cast[uint8](0)

  # Parse uptime (first number is seconds)
  var uptime_seconds: int32 = parse_int(buffer)

  # Convert to hours, minutes, seconds
  var hours: int32 = uptime_seconds / 3600
  var minutes: int32 = (uptime_seconds % 3600) / 60
  var seconds: int32 = uptime_seconds % 60

  # Print uptime
  print(cast[ptr uint8]("up "))
  print_int(hours)
  print(cast[ptr uint8](":"))
  print_int_pad(minutes)
  print(cast[ptr uint8](":"))
  print_int_pad(seconds)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
