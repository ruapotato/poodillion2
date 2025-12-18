# env - Run program in modified environment
# Usage: env (prints environment)
#        env VAR=VAL COMMAND (runs command with environment)

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_execve: int32 = 11

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

# String length
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

# String compare
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0) and s2[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      if s1[i] < s2[i]:
        return -1
      else:
        return 1
    i = i + 1
  if s1[i] == cast[uint8](0) and s2[i] == cast[uint8](0):
    return 0
  if s1[i] == cast[uint8](0):
    return -1
  return 1

# String copy
proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

# Print string
proc print(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

# Print error
proc print_err(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDERR, cast[int32](s), len)

# Check if string contains '=' (is an environment variable assignment)
proc is_env_var(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    if s[i] == cast[uint8](61):  # '='
      return 1
    i = i + 1
  return 0

# Read and print environment from /proc/self/environ
proc print_environ() =
  var fd: int32 = syscall3(SYS_open, cast[int32]("/proc/self/environ"), O_RDONLY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("env: cannot open /proc/self/environ\n"))
    discard syscall1(SYS_exit, 1)

  # Allocate read buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  # Read environment (null-separated strings)
  var total_read: int32 = 0
  while 1 == 1:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buf) + total_read, 8192 - total_read)
    if n <= 0:
      break
    total_read = total_read + n

  discard syscall1(SYS_close, fd)

  # Print each environment variable (replace null with newline)
  var i: int32 = 0
  var line_start: int32 = 0
  while i < total_read:
    if buf[i] == cast[uint8](0):
      if i > line_start:
        # Print line
        discard syscall3(SYS_write, STDOUT, cast[int32](buf) + line_start, i - line_start)
        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
      line_start = i + 1
    i = i + 1

proc main() =
  var argc: int32 = get_argc()

  # No arguments: print environment
  if argc == 1:
    print_environ()
    discard syscall1(SYS_exit, 0)

  # Allocate memory for building environment and argv
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384  # 16KB
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # 0-4096: envp array (256 pointers)
  # 4096-8192: argv array (256 pointers)
  # 8192-16384: environment storage
  var envp_array: ptr int32 = cast[ptr int32](old_brk)
  var argv_array: ptr int32 = cast[ptr int32](old_brk + 4096)
  var env_storage: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var env_pos: int32 = 0

  # Parse arguments
  var arg_idx: int32 = 1
  var env_count: int32 = 0

  # First, collect VAR=VAL assignments
  while arg_idx < argc:
    var arg: ptr uint8 = get_argv(arg_idx)
    if is_env_var(arg) == 0:
      break  # Not an env var, must be command

    # Copy to env storage
    var j: int32 = 0
    while arg[j] != cast[uint8](0):
      env_storage[env_pos + j] = arg[j]
      j = j + 1
    env_storage[env_pos + j] = cast[uint8](0)

    # Add to envp
    envp_array[env_count] = cast[int32](env_storage) + env_pos
    env_count = env_count + 1
    env_pos = env_pos + j + 1

    arg_idx = arg_idx + 1

  # Null terminate envp
  envp_array[env_count] = 0

  # If no command specified, just print environment vars
  if arg_idx >= argc:
    var i: int32 = 0
    while i < env_count:
      var env_str: ptr uint8 = cast[ptr uint8](envp_array[i])
      print(env_str)
      print(cast[ptr uint8]("\n"))
      i = i + 1
    discard syscall1(SYS_exit, 0)

  # Build argv for command
  var cmd_argc: int32 = 0
  while arg_idx < argc:
    argv_array[cmd_argc] = cast[int32](get_argv(arg_idx))
    cmd_argc = cmd_argc + 1
    arg_idx = arg_idx + 1

  # Null terminate argv
  argv_array[cmd_argc] = 0

  # Execute command
  var cmd: ptr uint8 = cast[ptr uint8](argv_array[0])
  var env_ptr: int32 = 0
  if env_count > 0:
    env_ptr = cast[int32](envp_array)

  discard syscall3(SYS_execve, cast[int32](cmd), cast[int32](argv_array), env_ptr)

  # If execve returns, it failed
  print_err(cast[ptr uint8]("env: exec failed\n"))
  discard syscall1(SYS_exit, 1)
