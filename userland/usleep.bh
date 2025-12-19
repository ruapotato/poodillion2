# usleep - Sleep for specified microseconds
# Usage: usleep MICROSECONDS

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_nanosleep: int32 = 162
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

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

# Parse unsigned integer from string
proc parse_uint(s: ptr uint8): uint32 =
  var result: uint32 = 0
  var i: int32 = 0
  while s[i] >= cast[uint8](48) and s[i] <= cast[uint8](57):
    result = result * 10 + cast[uint32](s[i]) - 48
    i = i + 1
  return result

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    print_err(cast[ptr uint8]("Usage: usleep MICROSECONDS\n"))
    discard syscall1(SYS_exit, 1)

  # Get microseconds argument
  var usec_arg: ptr uint8 = get_argv(1)
  var microseconds: uint32 = parse_uint(usec_arg)

  if microseconds == 0:
    discard syscall1(SYS_exit, 0)

  # Allocate space for timespec (8 bytes: 4 for sec, 4 for nsec)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16
  discard syscall1(SYS_brk, new_brk)
  var timespec: ptr uint32 = cast[ptr uint32](old_brk)

  # Convert microseconds to seconds and nanoseconds
  # 1 second = 1,000,000 microseconds
  # 1 microsecond = 1,000 nanoseconds
  var seconds: uint32 = microseconds / 1000000
  var remaining_usec: uint32 = microseconds % 1000000
  var nanoseconds: uint32 = remaining_usec * 1000

  timespec[0] = seconds
  timespec[1] = nanoseconds

  # Call nanosleep(req, rem)
  var result: int32 = syscall2(SYS_nanosleep, cast[int32](timespec), 0)

  if result < 0:
    print_err(cast[ptr uint8]("usleep: nanosleep failed\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
