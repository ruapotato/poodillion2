# xargs - Build and execute command lines from stdin
# Usage: xargs COMMAND
# Reads lines from stdin and passes them as arguments to COMMAND

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_fork: int32 = 2
const SYS_execve: int32 = 11
const SYS_wait4: int32 = 114

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc syscall4(num: int32, arg1: int32, arg2: int32, arg3: int32, arg4: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

# String length
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

# Print error
proc print_err(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDERR, cast[int32](s), len)

# Read line from stdin into buffer (returns length, -1 on EOF)
proc read_line(buf: ptr uint8, max_len: int32): int32 =
  var i: int32 = 0
  while i < max_len - 1:
    var ch: uint8
    var n: int32 = syscall3(SYS_read, STDIN, cast[int32](addr(ch)), 1)
    if n <= 0:
      if i == 0:
        return -1  # EOF
      buf[i] = cast[uint8](0)
      return i
    if ch == cast[uint8](10):  # newline
      buf[i] = cast[uint8](0)
      return i
    buf[i] = ch
    i = i + 1
  buf[i] = cast[uint8](0)
  return i

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    print_err(cast[ptr uint8]("Usage: xargs COMMAND\n"))
    discard syscall1(SYS_exit, 1)

  # Allocate memory for buffers
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384  # 16KB
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # 0-4096: line buffer
  # 4096-8192: argv array (max 256 pointers)
  # 8192-16384: argument strings storage
  var line_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var argv_array: ptr int32 = cast[ptr int32](old_brk + 4096)
  var arg_storage: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var arg_storage_pos: int32 = 0

  # Build base argv (command and its args)
  var base_argc: int32 = argc - 1
  var i: int32 = 0
  while i < base_argc:
    argv_array[i] = cast[int32](get_argv(i + 1))
    i = i + 1

  # Read lines from stdin
  while 1 == 1:
    var line_len: int32 = read_line(line_buf, 4096)
    if line_len < 0:
      break  # EOF

    if line_len == 0:
      # Empty line, skip
      var skip: int32 = 1
      if skip != 0:
        # no-op to avoid continue
        skip = 0
      else:
        # Copy line to storage
        var j: int32 = 0
        while j <= line_len:  # include null terminator
          arg_storage[arg_storage_pos + j] = line_buf[j]
          j = j + 1

        # Add to argv
        argv_array[base_argc] = cast[int32](arg_storage) + arg_storage_pos
        arg_storage_pos = arg_storage_pos + line_len + 1

        # Null terminate argv
        argv_array[base_argc + 1] = 0

        # Fork and exec
        var pid: int32 = syscall1(SYS_fork, 0)
        if pid == 0:
          # Child process
          var cmd: ptr uint8 = cast[ptr uint8](argv_array[0])
          discard syscall3(SYS_execve, cast[int32](cmd), cast[int32](argv_array), 0)
          # If execve fails
          print_err(cast[ptr uint8]("xargs: exec failed\n"))
          discard syscall1(SYS_exit, 1)
        else:
          # Parent process - wait for child
          discard syscall4(SYS_wait4, pid, 0, 0, 0)

        # Reset for next line
        arg_storage_pos = 0
    else:
      # Copy line to storage
      var j: int32 = 0
      while j <= line_len:
        arg_storage[arg_storage_pos + j] = line_buf[j]
        j = j + 1

      # Add to argv
      argv_array[base_argc] = cast[int32](arg_storage) + arg_storage_pos
      arg_storage_pos = arg_storage_pos + line_len + 1

      # Null terminate argv
      argv_array[base_argc + 1] = 0

      # Fork and exec
      var pid: int32 = syscall1(SYS_fork, 0)
      if pid == 0:
        # Child process
        var cmd: ptr uint8 = cast[ptr uint8](argv_array[0])
        discard syscall3(SYS_execve, cast[int32](cmd), cast[int32](argv_array), 0)
        print_err(cast[ptr uint8]("xargs: exec failed\n"))
        discard syscall1(SYS_exit, 1)
      else:
        # Parent - wait
        discard syscall4(SYS_wait4, pid, 0, 0, 0)

      # Reset
      arg_storage_pos = 0

  discard syscall1(SYS_exit, 0)
