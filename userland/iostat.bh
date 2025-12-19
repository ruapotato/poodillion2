# iostat - I/O statistics
# Displays disk I/O statistics from /proc/diskstats
# Format: Device tps kB_read/s kB_wrtn/s

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

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Parse integer from string
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  # Skip leading whitespace
  while s[i] == cast[uint8](32):
    i = i + 1
  while s[i] >= cast[uint8](48):
    if s[i] > cast[uint8](57):
      break
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

# Skip whitespace
proc skip_whitespace(s: ptr uint8, pos: int32): int32 =
  var i: int32 = pos
  while s[i] == cast[uint8](32):
    i = i + 1
  return i

# Skip to next whitespace
proc skip_to_whitespace(s: ptr uint8, pos: int32): int32 =
  var i: int32 = pos
  while s[i] != cast[uint8](0):
    if s[i] == cast[uint8](32):
      return i
    if s[i] == cast[uint8](10):
      return i
    i = i + 1
  return i

# Print integer with padding
proc print_int_padded(n: int32, width: int32) =
  if n == 0:
    var spaces: int32 = width - 1
    while spaces > 0:
      discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
      spaces = spaces - 1
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n
  var neg: int32 = 0

  if num < 0:
    neg = 1
    num = 0 - num

  # Count digits
  var temp: int32 = num
  var digits: int32 = 0
  while temp > 0:
    digits = digits + 1
    temp = temp / 10

  if neg == 1:
    digits = digits + 1

  # Print padding spaces
  var spaces: int32 = width - digits
  while spaces > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
    spaces = spaces - 1

  # Print sign
  if neg == 1:
    discard syscall3(SYS_write, STDOUT, cast[int32]("-"), 1)

  # Print number
  temp = num
  var reversed: int32 = 0
  var count: int32 = 0
  while temp > 0:
    reversed = reversed * 10 + (temp % 10)
    temp = temp / 10
    count = count + 1

  while count > 0:
    var d: uint8 = cast[uint8](48 + (reversed % 10))
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(d)), 1)
    reversed = reversed / 10
    count = count - 1

# Print string with padding
proc print_str_padded(s: ptr uint8, width: int32) =
  var len: int32 = strlen(s)

  # Print string
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

  # Print padding spaces
  var spaces: int32 = width - len
  while spaces > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
    spaces = spaces - 1

# Copy device name (up to max_len)
proc copy_device_name(dest: ptr uint8, src: ptr uint8, max_len: int32) =
  var i: int32 = 0
  while i < max_len - 1:
    if src[i] == cast[uint8](0):
      break
    if src[i] == cast[uint8](32):
      break
    if src[i] == cast[uint8](10):
      break
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # +0: diskstats buffer (8KB)
  # +8192: path buffer (256 bytes)
  # +8448: device name buffer (256 bytes)
  var diskstats_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var device_name: ptr uint8 = cast[ptr uint8](old_brk + 8448)

  # Build path: /proc/diskstats
  path_buf[0] = cast[uint8](47)   # /
  path_buf[1] = cast[uint8](112)  # p
  path_buf[2] = cast[uint8](114)  # r
  path_buf[3] = cast[uint8](111)  # o
  path_buf[4] = cast[uint8](99)   # c
  path_buf[5] = cast[uint8](47)   # /
  path_buf[6] = cast[uint8](100)  # d
  path_buf[7] = cast[uint8](105)  # i
  path_buf[8] = cast[uint8](115)  # s
  path_buf[9] = cast[uint8](107)  # k
  path_buf[10] = cast[uint8](115) # s
  path_buf[11] = cast[uint8](116) # t
  path_buf[12] = cast[uint8](97)  # a
  path_buf[13] = cast[uint8](116) # t
  path_buf[14] = cast[uint8](115) # s
  path_buf[15] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("iostat: cannot open /proc/diskstats\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](diskstats_buf), 8191)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print_err(cast[ptr uint8]("iostat: cannot read /proc/diskstats\n"))
    discard syscall1(SYS_exit, 1)

  diskstats_buf[nread] = cast[uint8](0)

  # Print header
  print(cast[ptr uint8]("Device             tps    kB_read/s    kB_wrtn/s\n"))

  # Parse /proc/diskstats
  # Format: major minor name reads reads_merged reads_sectors reads_ms
  #         writes writes_merged writes_sectors writes_ms
  #         ios_in_progress time_in_ios weighted_time_in_ios

  var i: int32 = 0
  while i < nread:
    # Skip leading whitespace
    i = skip_whitespace(diskstats_buf, i)

    if diskstats_buf[i] == cast[uint8](0):
      break

    # Skip major number
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Skip minor number
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Get device name (field 3)
    var name_start: int32 = i
    copy_device_name(device_name, cast[ptr uint8](cast[int32](diskstats_buf) + name_start), 16)
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Get reads completed (field 4)
    var reads: int32 = parse_int(cast[ptr uint8](cast[int32](diskstats_buf) + i))
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Skip reads_merged (field 5)
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Get sectors read (field 6)
    var sectors_read: int32 = parse_int(cast[ptr uint8](cast[int32](diskstats_buf) + i))
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Skip time reading (field 7)
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Get writes completed (field 8)
    var writes: int32 = parse_int(cast[ptr uint8](cast[int32](diskstats_buf) + i))
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Skip writes_merged (field 9)
    i = skip_to_whitespace(diskstats_buf, i)
    i = skip_whitespace(diskstats_buf, i)

    # Get sectors written (field 10)
    var sectors_written: int32 = parse_int(cast[ptr uint8](cast[int32](diskstats_buf) + i))

    # Skip to end of line
    while diskstats_buf[i] != cast[uint8](10):
      if diskstats_buf[i] == cast[uint8](0):
        break
      i = i + 1
    if diskstats_buf[i] == cast[uint8](10):
      i = i + 1

    # Calculate statistics
    # tps = reads + writes (we don't have time data, so this is cumulative)
    # Sectors are 512 bytes, so divide by 2 to get KB
    var tps: int32 = reads + writes
    var kb_read: int32 = sectors_read / 2
    var kb_written: int32 = sectors_written / 2

    # Only show devices with activity
    if tps > 0:
      print_str_padded(device_name, 16)
      print_int_padded(tps, 8)
      print_int_padded(kb_read, 13)
      print_int_padded(kb_written, 13)
      print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
