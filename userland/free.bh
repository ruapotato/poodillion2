# free - Display amount of free and used memory in the system
# Parses /proc/meminfo to extract memory statistics

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

# Compare strings up to n characters
proc strncmp(s1: ptr uint8, s2: ptr uint8, n: int32): int32 =
  var i: int32 = 0
  while i < n:
    if s1[i] != s2[i]:
      if s1[i] < s2[i]:
        return -1
      return 1
    if s1[i] == cast[uint8](0):
      return 0
    i = i + 1
  return 0

# Parse integer from string (skip non-digits)
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  # Skip non-digits
  while s[i] != cast[uint8](0):
    if s[i] >= cast[uint8](48):
      if s[i] <= cast[uint8](57):
        result = result * 10 + cast[int32](s[i]) - 48
        i = i + 1
        # Continue parsing
        while s[i] >= cast[uint8](48):
          if s[i] <= cast[uint8](57):
            result = result * 10 + cast[int32](s[i]) - 48
          i = i + 1
        return result
    i = i + 1
  return result

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var neg: int32 = 0
  var num: int32 = n
  if num < 0:
    neg = 1
    num = 0 - num

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
  if neg == 1:
    pos = pos + 1

  buf[pos] = cast[uint8](0)
  pos = pos - 1

  temp = num
  while temp > 0:
    var digit: int32 = temp % 10
    buf[pos] = cast[uint8](48 + digit)
    pos = pos - 1
    temp = temp / 10

  if neg == 1:
    buf[0] = cast[uint8](45)

  print(buf)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build path: /proc/meminfo
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](109)  # m
  path[7] = cast[uint8](101)  # e
  path[8] = cast[uint8](109)  # m
  path[9] = cast[uint8](105)  # i
  path[10] = cast[uint8](110) # n
  path[11] = cast[uint8](102) # f
  path[12] = cast[uint8](111) # o
  path[13] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print(cast[ptr uint8]("free: cannot open /proc/meminfo\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print(cast[ptr uint8]("free: cannot read /proc/meminfo\n"))
    discard syscall1(SYS_exit, 1)

  buffer[nread] = cast[uint8](0)

  # Parse meminfo
  var mem_total: int32 = 0
  var mem_free: int32 = 0
  var mem_available: int32 = 0
  var buffers: int32 = 0
  var cached: int32 = 0

  var i: int32 = 0
  while i < nread:
    # Check for "MemTotal:"
    if strncmp(cast[ptr uint8](cast[int32](buffer) + i), cast[ptr uint8]("MemTotal:"), 9) == 0:
      mem_total = parse_int(cast[ptr uint8](cast[int32](buffer) + i + 9))
    # Check for "MemFree:"
    if strncmp(cast[ptr uint8](cast[int32](buffer) + i), cast[ptr uint8]("MemFree:"), 8) == 0:
      mem_free = parse_int(cast[ptr uint8](cast[int32](buffer) + i + 8))
    # Check for "MemAvailable:"
    if strncmp(cast[ptr uint8](cast[int32](buffer) + i), cast[ptr uint8]("MemAvailable:"), 13) == 0:
      mem_available = parse_int(cast[ptr uint8](cast[int32](buffer) + i + 13))
    # Check for "Buffers:"
    if strncmp(cast[ptr uint8](cast[int32](buffer) + i), cast[ptr uint8]("Buffers:"), 8) == 0:
      buffers = parse_int(cast[ptr uint8](cast[int32](buffer) + i + 8))
    # Check for "Cached:"
    if strncmp(cast[ptr uint8](cast[int32](buffer) + i), cast[ptr uint8]("Cached:"), 7) == 0:
      cached = parse_int(cast[ptr uint8](cast[int32](buffer) + i + 7))

    # Skip to next line
    while i < nread:
      if buffer[i] == cast[uint8](10):  # newline
        i = i + 1
        break
      i = i + 1

  # Calculate used memory
  var mem_used: int32 = mem_total - mem_free - buffers - cached

  # Print results
  print(cast[ptr uint8]("              total        used        free      shared  buff/cache   available\n"))
  print(cast[ptr uint8]("Mem:        "))
  print_int(mem_total)
  print(cast[ptr uint8]("        "))
  print_int(mem_used)
  print(cast[ptr uint8]("        "))
  print_int(mem_free)
  print(cast[ptr uint8]("           0        "))
  print_int(buffers + cached)
  print(cast[ptr uint8]("        "))
  print_int(mem_available)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
