# timeout - Run command with time limit
# Usage: timeout SECONDS COMMAND [ARGS...]
# Exit with 124 if timeout, else command's exit code

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_fork: int32 = 2
const SYS_waitpid: int32 = 7
const SYS_alarm: int32 = 27
const SYS_kill: int32 = 37
const SYS_execve: int32 = 11
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

const SIGTERM: int32 = 15
const SIGKILL: int32 = 9
const SIGALRM: int32 = 14

const WNOHANG: int32 = 1

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

proc atoi(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] >= cast[uint8](48) and s[i] <= cast[uint8](57):
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: timeout SECONDS COMMAND [ARGS...]\n"))
    discard syscall1(SYS_exit, 1)

  # Get timeout value
  var timeout_arg: ptr uint8 = get_argv(1)
  var timeout_seconds: int32 = atoi(timeout_arg)

  if timeout_seconds <= 0:
    print_err(cast[ptr uint8]("timeout: invalid timeout value\n"))
    discard syscall1(SYS_exit, 1)

  # Fork to run the command
  var pid: int32 = syscall1(SYS_fork, 0)

  if pid < 0:
    print_err(cast[ptr uint8]("timeout: fork failed\n"))
    discard syscall1(SYS_exit, 1)

  if pid == 0:
    # Child process - exec the command
    # Build argv array for command (skip "timeout" and seconds)
    var old_brk: int32 = syscall1(SYS_brk, 0)
    var new_brk: int32 = old_brk + 4096
    discard syscall1(SYS_brk, new_brk)

    var argv: ptr int32 = cast[ptr int32](old_brk)
    var i: int32 = 2
    var arg_idx: int32 = 0
    while i < argc:
      argv[arg_idx] = cast[int32](get_argv(i))
      arg_idx = arg_idx + 1
      i = i + 1
    argv[arg_idx] = 0  # NULL terminate

    # Exec the command
    var cmd: ptr uint8 = get_argv(2)
    discard syscall3(SYS_execve, cast[int32](cmd), cast[int32](argv), 0)

    # If execve returns, it failed
    print_err(cast[ptr uint8]("timeout: cannot execute command\n"))
    discard syscall1(SYS_exit, 127)

  # Parent process - wait with timeout
  # Set alarm for timeout
  discard syscall1(SYS_alarm, timeout_seconds)

  # Wait for child
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16
  discard syscall1(SYS_brk, new_brk)
  var status: ptr int32 = cast[ptr int32](old_brk)
  status[0] = 0

  var result: int32 = syscall3(SYS_waitpid, pid, cast[int32](status), 0)

  # Cancel alarm
  discard syscall1(SYS_alarm, 0)

  if result < 0:
    # Wait failed - might be because alarm interrupted it
    # Try to kill the child
    discard syscall2(SYS_kill, pid, SIGTERM)

    # Wait a bit and then SIGKILL
    # (simplified: just send SIGKILL)
    discard syscall2(SYS_kill, pid, SIGKILL)

    # Try to reap the child
    discard syscall3(SYS_waitpid, pid, cast[int32](status), 0)

    print_err(cast[ptr uint8]("timeout: command timed out\n"))
    discard syscall1(SYS_exit, 124)

  # Extract exit code from status
  # status is in the format: low byte = signal, next byte = exit code
  var exit_code: int32 = (status[0] / 256) % 256

  discard syscall1(SYS_exit, exit_code)
