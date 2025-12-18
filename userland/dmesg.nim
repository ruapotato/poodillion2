# dmesg - Print kernel ring buffer messages
# Uses SYS_syslog (103) to read kernel messages
# Part of PoodillionOS kernel utilities

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_syslog: int32 = 103
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

# syslog types
const SYSLOG_ACTION_READ_ALL: int32 = 3
const SYSLOG_ACTION_SIZE_BUFFER: int32 = 10

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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
  # Allocate memory for kernel log buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)

  # Try to get buffer size first
  var bufsize: int32 = syscall2(SYS_syslog, SYSLOG_ACTION_SIZE_BUFFER, 0)

  # If that fails, use a reasonable default (256KB)
  if bufsize <= 0:
    bufsize = 262144

  # Limit to 1MB to avoid excessive memory usage
  if bufsize > 1048576:
    bufsize = 1048576

  # Allocate buffer
  var new_brk: int32 = old_brk + bufsize
  discard syscall1(SYS_brk, new_brk)

  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read all kernel messages (type 3 = SYSLOG_ACTION_READ_ALL)
  var nread: int32 = syscall3(SYS_syslog, SYSLOG_ACTION_READ_ALL, cast[int32](buffer), bufsize)

  if nread < 0:
    print_error(cast[ptr uint8]("dmesg: failed to read kernel log\n"))
    print_error(cast[ptr uint8]("dmesg: are you root? try: sudo dmesg\n"))
    discard syscall1(SYS_exit, 1)

  if nread == 0:
    # Empty kernel log - this is unusual but not an error
    discard syscall1(SYS_exit, 0)

  # Print the kernel log buffer
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer), nread)

  # Add newline if buffer doesn't end with one
  if nread > 0:
    if buffer[nread - 1] != cast[uint8](10):
      print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
