# getty - Get TTY and spawn login
# Getty opens a tty, sets it up, displays a login prompt, and execs login
#
# Usage: getty /dev/tty1
#
# Simple implementation:
# - Opens the specified tty device
# - Redirects stdin/stdout/stderr to the tty
# - Displays a banner
# - Execs login (or shell directly if login not available)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_dup2: int32 = 63
const SYS_execve: int32 = 11
const SYS_brk: int32 = 45
const SYS_setsid: int32 = 66
const SYS_ioctl: int32 = 54

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

# Open flags
const O_RDWR: int32 = 2
const O_NOCTTY: int32 = 256

# ioctl commands for terminal control
const TIOCSCTTY: uint32 = 0x540E  # Make this tty the controlling terminal

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

proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    print_err(cast[ptr uint8]("getty: usage: getty /dev/ttyN\n"))
    discard syscall1(SYS_exit, 1)

  var tty_path: ptr uint8 = get_argv(1)

  # Create a new session
  # This makes the process a session leader
  var sid: int32 = syscall1(SYS_setsid, 0)
  if sid < 0:
    print_err(cast[ptr uint8]("getty: warning: setsid failed\n"))

  # Open the tty device
  var fd: int32 = syscall2(SYS_open, cast[int32](tty_path), O_RDWR)

  if fd < 0:
    print_err(cast[ptr uint8]("getty: failed to open "))
    print_err(tty_path)
    print_err(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 1)

  # Make this tty our controlling terminal
  # TIOCSCTTY = 0x540E (make terminal our controlling tty)
  var ioctl_result: int32 = syscall3(SYS_ioctl, fd, cast[int32](TIOCSCTTY), 0)
  if ioctl_result < 0:
    print_err(cast[ptr uint8]("getty: warning: ioctl TIOCSCTTY failed\n"))

  # Redirect stdin, stdout, stderr to the tty
  if fd != STDIN:
    discard syscall2(SYS_dup2, fd, STDIN)
  if fd != STDOUT:
    discard syscall2(SYS_dup2, fd, STDOUT)
  if fd != STDERR:
    discard syscall2(SYS_dup2, fd, STDERR)

  # Close the original fd if it's not 0, 1, or 2
  if fd > 2:
    discard syscall1(SYS_close, fd)

  # Display banner
  print(cast[ptr uint8]("PoodillionOS v0.1 Alpha\n"))
  print(cast[ptr uint8]("The Future of Computing\n"))

  # Allocate memory for argv
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 512
  discard syscall1(SYS_brk, new_brk)
  var argv: ptr int32 = cast[ptr int32](old_brk)
  var login_path: ptr uint8 = cast[ptr uint8](old_brk + 64)

  # Try to exec login
  # argv[0] = "/bin/login"
  # argv[1] = NULL
  strcpy(login_path, cast[ptr uint8]("/bin/login"))
  argv[0] = cast[int32](login_path)
  argv[1] = 0

  discard syscall3(SYS_execve, cast[int32](login_path), cast[int32](argv), 0)

  # If that fails, try ./bin/login
  strcpy(login_path, cast[ptr uint8]("./bin/login"))
  argv[0] = cast[int32](login_path)
  discard syscall3(SYS_execve, cast[int32](login_path), cast[int32](argv), 0)

  # If login doesn't exist, exec shell directly
  strcpy(login_path, cast[ptr uint8]("/bin/psh"))
  argv[0] = cast[int32](login_path)
  discard syscall3(SYS_execve, cast[int32](login_path), cast[int32](argv), 0)

  # Try ./bin/psh
  strcpy(login_path, cast[ptr uint8]("./bin/psh"))
  argv[0] = cast[int32](login_path)
  discard syscall3(SYS_execve, cast[int32](login_path), cast[int32](argv), 0)

  # If everything fails, show error and exit
  print_err(cast[ptr uint8]("getty: failed to exec login or shell\n"))
  discard syscall1(SYS_exit, 1)
