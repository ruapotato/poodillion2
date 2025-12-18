# wait - Wait for process completion
# Usage: wait [PID]
# If no PID, wait for all children

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_waitpid: int32 = 7
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

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Parse integer from string
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

# Print integer
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

  # Allocate memory for status
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16
  discard syscall1(SYS_brk, new_brk)
  var status: ptr int32 = cast[ptr int32](old_brk)

  var pid_to_wait: int32 = -1  # -1 means wait for any child

  if argc >= 2:
    var pid_arg: ptr uint8 = get_argv(1)
    pid_to_wait = atoi(pid_arg)

    if pid_to_wait <= 0:
      print_err(cast[ptr uint8]("wait: invalid PID\n"))
      discard syscall1(SYS_exit, 1)

  # Wait for process
  status[0] = 0
  var result: int32 = syscall3(SYS_waitpid, pid_to_wait, cast[int32](status), 0)

  if result < 0:
    print_err(cast[ptr uint8]("wait: no child process\n"))
    discard syscall1(SYS_exit, 127)

  # Print which PID we waited for
  print(cast[ptr uint8]("wait: process "))
  print_int(result)
  print(cast[ptr uint8](" exited with status "))

  # Extract exit code from status
  var exit_code: int32 = (status[0] / 256) % 256
  print_int(exit_code)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
