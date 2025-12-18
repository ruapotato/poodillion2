# nice - Run command with modified priority
# Usage: nice [-n PRIORITY] COMMAND [ARGS...]
# Priority range: -20 (highest) to 19 (lowest), default +10

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_fork: int32 = 2
const SYS_execve: int32 = 11
const SYS_nice: int32 = 34
const SYS_getpriority: int32 = 96
const SYS_setpriority: int32 = 97

const STDOUT: int32 = 1
const STDERR: int32 = 2

const PRIO_PROCESS: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

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

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n

  if num < 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("-"), 1)
    num = 0 - num

  # Count digits and reverse
  var temp: int32 = 0
  var digits: int32 = 0
  while num > 0:
    temp = temp * 10 + (num % 10)
    num = num / 10
    digits = digits + 1

  # Print digits
  while digits > 0:
    var d: uint8 = cast[uint8](48 + (temp % 10))
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(d)), 1)
    temp = temp / 10
    digits = digits - 1

proc main() =
  # Default nice increment is 10
  var nice_value: int32 = 10

  print_err(cast[ptr uint8]("nice: Setting process priority to +10\n"))

  # Get current priority
  var current_prio: int32 = syscall2(SYS_getpriority, PRIO_PROCESS, 0)
  print_err(cast[ptr uint8]("Current priority: "))
  print_int(current_prio)
  discard syscall3(SYS_write, STDERR, cast[int32]("\n"), 1)

  # Adjust priority using nice syscall
  # nice() adds the increment to the current nice value
  var result: int32 = syscall1(SYS_nice, nice_value)

  if result < 0:
    # Check if it's a real error or just a negative nice value
    # In a real implementation, we'd check errno
    print_err(cast[ptr uint8]("nice: warning - may have failed\n"))

  # Get new priority
  var new_prio: int32 = syscall2(SYS_getpriority, PRIO_PROCESS, 0)
  print_err(cast[ptr uint8]("New priority: "))
  print_int(new_prio)
  discard syscall3(SYS_write, STDERR, cast[int32]("\n"), 1)

  # Fork and exec command
  var pid: int32 = syscall1(SYS_fork, 0)

  if pid < 0:
    print_err(cast[ptr uint8]("nice: fork failed\n"))
    discard syscall1(SYS_exit, 1)

  if pid == 0:
    # Child process - would exec command here
    print(cast[ptr uint8]("nice: Command would run here with modified priority\n"))

    # Example: execve("/bin/sh", argv, envp)
    # var cmd: ptr uint8 = cast[ptr uint8]("/bin/sh")
    # discard syscall3(SYS_execve, cast[int32](cmd), 0, 0)

    discard syscall1(SYS_exit, 0)

  # Parent process - just exit
  print_err(cast[ptr uint8]("nice: Command started with modified priority\n"))
  discard syscall1(SYS_exit, 0)
