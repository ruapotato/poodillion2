# renice - Alter priority of running process
# Usage: renice PRIORITY PID
# Priority range: -20 (highest) to 19 (lowest)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_setpriority: int32 = 97
const SYS_getpriority: int32 = 96

const STDOUT: int32 = 1
const STDERR: int32 = 2

const PRIO_PROCESS: int32 = 0

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

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Parse integer from string (handles negative)
proc atoi(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0

  # Skip leading whitespace
  while s[i] == cast[uint8](32):
    i = i + 1

  # Handle negative
  var neg: int32 = 0
  if s[i] == cast[uint8](45):  # '-'
    neg = 1
    i = i + 1

  while s[i] >= cast[uint8](48) and s[i] <= cast[uint8](57):
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1

  if neg == 1:
    result = 0 - result

  return result

# Print integer (handles negative)
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n

  if num < 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("-"), 1)
    num = 0 - num

  var temp: int32 = 0
  var digits: int32 = 0

  while num > 0:
    temp = temp * 10 + (num % 10)
    num = num / 10
    digits = digits + 1

  while digits > 0:
    var d: uint8 = cast[uint8](48 + (temp % 10))
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(d)), 1)
    temp = temp / 10
    digits = digits - 1

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: renice PRIORITY PID\n"))
    print_err(cast[ptr uint8]("  Priority range: -20 (highest) to 19 (lowest)\n"))
    discard syscall1(SYS_exit, 1)

  # Get priority and PID
  var priority_arg: ptr uint8 = get_argv(1)
  var pid_arg: ptr uint8 = get_argv(2)

  var priority: int32 = atoi(priority_arg)
  var pid: int32 = atoi(pid_arg)

  if pid <= 0:
    print_err(cast[ptr uint8]("renice: invalid PID\n"))
    discard syscall1(SYS_exit, 1)

  if priority < -20 or priority > 19:
    print_err(cast[ptr uint8]("renice: priority must be between -20 and 19\n"))
    discard syscall1(SYS_exit, 1)

  # Get current priority
  var current_prio: int32 = syscall2(SYS_getpriority, PRIO_PROCESS, pid)

  # Set new priority
  var result: int32 = syscall3(SYS_setpriority, PRIO_PROCESS, pid, priority)

  if result < 0:
    print_err(cast[ptr uint8]("renice: failed to set priority (permission denied?)\n"))
    discard syscall1(SYS_exit, 1)

  # Confirm change
  print(cast[ptr uint8]("renice: PID "))
  print_int(pid)
  print(cast[ptr uint8](" priority changed from "))
  print_int(current_prio)
  print(cast[ptr uint8](" to "))
  print_int(priority)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
