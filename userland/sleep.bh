# sleep - Sleep for N seconds
# Usage: sleep SECONDS

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_nanosleep: int32 = 162

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

const SYS_brk: int32 = 45

extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

proc atoi(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] >= cast[uint8](48) and s[i] <= cast[uint8](57):
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

proc main() =
  var argc: int32 = get_argc()
  var seconds: int32 = 1

  if argc >= 2:
    var arg: ptr uint8 = get_argv(1)
    seconds = atoi(arg)

  if seconds <= 0:
    seconds = 1

  # Allocate space for timespec (8 bytes: 4 for sec, 4 for nsec)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16
  discard syscall1(SYS_brk, new_brk)
  var timespec: ptr int32 = cast[ptr int32](old_brk)
  timespec[0] = seconds  # seconds
  timespec[1] = 0        # nanoseconds

  # Call nanosleep(req, rem)
  var result: int32 = syscall2(SYS_nanosleep, cast[int32](timespec), 0)

  if result < 0:
    print_err(cast[ptr uint8]("sleep: nanosleep failed\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
