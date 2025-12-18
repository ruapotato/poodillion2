# psh - PoodillionOS Type-Aware Shell
# A badass shell that understands structured data and schemas!

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_fork: int32 = 2
const SYS_execve: int32 = 11
const SYS_waitpid: int32 = 7
const SYS_pipe: int32 = 42
const SYS_dup2: int32 = 63
const SYS_close: int32 = 6
const SYS_brk: int32 = 45
const SYS_chdir: int32 = 12
const SYS_getcwd: int32 = 183
const SYS_open: int32 = 5
const SYS_readlink: int32 = 89
const SYS_access: int32 = 33

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# Global state for shell (allocated in main)
var g_cwd_buf: ptr uint8
var g_prev_dir: ptr uint8
var g_home_dir: ptr uint8
var g_history: ptr int32  # Array of string pointers
var g_history_count: int32 = 0
var g_history_storage: ptr uint8  # Buffer for history strings

# Print utilities
proc print(msg: ptr uint8) =
  var i: int32 = 0
  while msg[i] != cast[uint8](0):
    i = i + 1
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), i)

proc println(msg: ptr uint8) =
  print(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

proc print_err(msg: ptr uint8) =
  var i: int32 = 0
  while msg[i] != cast[uint8](0):
    i = i + 1
  discard syscall3(SYS_write, STDERR, cast[int32](msg), i)

# Print number
proc print_num(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var temp: int32 = n
  var count: int32 = 0
  while temp > 0:
    var digit: int32 = temp % 10
    buf[count] = cast[uint8](48 + digit)
    count = count + 1
    temp = temp / 10

  var i: int32 = count - 1
  while i >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(buf[i])), 1)
    i = i - 1

# String utilities
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return 1
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 1
  return 0

proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

# Concatenate two strings
proc strcat(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while dest[i] != cast[uint8](0):
    i = i + 1
  var j: int32 = 0
  while src[j] != cast[uint8](0):
    dest[i] = src[j]
    i = i + 1
    j = j + 1
  dest[i] = cast[uint8](0)

# Check if file exists and is executable (simplified)
proc file_exists(path: ptr uint8): int32 =
  var result: int32 = syscall2(SYS_access, cast[int32](path), 0)  # F_OK = 0
  if result == 0:
    return 1
  return 0

# Try to find command in PATH directories
# Returns pointer to resolved path in path_buf, or original cmd if not found
proc resolve_path(cmd: ptr uint8, path_buf: ptr uint8): ptr uint8 =
  # If command starts with / or ./, use as-is
  if cmd[0] == cast[uint8](47):  # '/'
    strcpy(path_buf, cmd)
    return path_buf
  if cmd[0] == cast[uint8](46):  # '.'
    strcpy(path_buf, cmd)
    return path_buf

  # Try ./bin/
  strcpy(path_buf, cast[ptr uint8]("./bin/"))
  strcat(path_buf, cmd)
  if file_exists(path_buf) != 0:
    return path_buf

  # Try /bin/
  strcpy(path_buf, cast[ptr uint8]("/bin/"))
  strcat(path_buf, cmd)
  if file_exists(path_buf) != 0:
    return path_buf

  # Try /usr/bin/
  strcpy(path_buf, cast[ptr uint8]("/usr/bin/"))
  strcat(path_buf, cmd)
  if file_exists(path_buf) != 0:
    return path_buf

  # Not found, return original with ./ prefix if needed
  if cmd[0] == cast[uint8](47):  # starts with '/'
    strcpy(path_buf, cmd)
  else:
    strcpy(path_buf, cast[ptr uint8]("./"))
    strcat(path_buf, cmd)
  return path_buf

# Get current working directory
# Returns length of path on success, -1 on error
proc get_cwd(buf: ptr uint8, size: int32): int32 =
  var result: int32 = syscall2(SYS_getcwd, cast[int32](buf), size)
  if result < 0:
    return -1
  return strlen(buf)

# Built-in: pwd - Print working directory
# Uses g_cwd_buf for temp storage
proc builtin_pwd(): int32 =
  var len: int32 = get_cwd(g_cwd_buf, 512)
  if len < 0:
    print_err(cast[ptr uint8]("pwd: error getting current directory\n"))
    return 1

  println(g_cwd_buf)
  return 0

# Built-in: cd - Change directory
proc builtin_cd(arg: ptr uint8): int32 =
  var target: ptr uint8

  # Handle different cd arguments
  if arg == cast[ptr uint8](0):
    # cd with no args - go to home
    target = g_home_dir
  else:
    # cd path - go to specified path
    target = arg

  var result: int32 = syscall1(SYS_chdir, cast[int32](target))
  if result != 0:
    print_err(cast[ptr uint8]("cd: "))
    print_err(target)
    print_err(cast[ptr uint8](": No such file or directory\n"))
    return 1

  return 0

# Built-in: env - Display environment variables
proc builtin_env(): int32 =
  # Read /proc/self/environ
  var fd: int32 = syscall3(SYS_open, cast[int32]("/proc/self/environ"), 0, 0)  # O_RDONLY
  if fd < 0:
    print_err(cast[ptr uint8]("env: cannot open /proc/self/environ\n"))
    return 1

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var n: int32 = syscall3(SYS_read, fd, cast[int32](buf), 8000)
  discard syscall1(SYS_close, fd)

  if n <= 0:
    print_err(cast[ptr uint8]("env: error reading environment\n"))
    return 1

  # Environment variables are null-separated, print each one
  var i: int32 = 0
  while i < n:
    if buf[i] == cast[uint8](0):
      discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
      i = i + 1
    else:
      var start: int32 = i
      while i < n:
        if buf[i] == cast[uint8](0):
          break
        i = i + 1
      discard syscall3(SYS_write, STDOUT, cast[int32](buf) + start, i - start)

  return 0

# Built-in: history - Display command history
proc builtin_history(): int32 =
  var i: int32 = 0
  while i < g_history_count:
    # Print command (without line numbers to avoid brk issues)
    var cmd_ptr: ptr uint8 = cast[ptr uint8](g_history[i])
    println(cmd_ptr)
    i = i + 1
  return 0

# Add command to history
proc add_to_history(cmd: ptr uint8) =
  var cmd_len: int32 = strlen(cmd)
  if cmd_len == 0:
    return

  # Use a circular buffer approach to avoid shifting
  # For now, limit to 20 commands, then stop adding (simpler)
  if g_history_count < 20:
    # Calculate storage offset for this command
    var storage_offset: int32 = g_history_count * 256
    var dest: ptr uint8 = cast[ptr uint8](cast[int32](g_history_storage) + storage_offset)

    # Copy command to storage
    strcpy(dest, cmd)

    # Store pointer in history array
    g_history[g_history_count] = cast[int32](dest)
    g_history_count = g_history_count + 1

# Check if command is a built-in and execute it
# Returns 1 if it was a built-in, 0 if not, -1 on error
# cmd_buf should be pre-allocated by caller
proc try_builtin_impl(trimmed: ptr uint8, cmd_buf: ptr uint8): int32 =
  var i: int32 = 0
  while trimmed[i] != cast[uint8](0):
    if trimmed[i] == cast[uint8](32):  # space
      break
    cmd_buf[i] = trimmed[i]
    i = i + 1
  cmd_buf[i] = cast[uint8](0)

  # Find argument (skip spaces)
  while trimmed[i] == cast[uint8](32):
    i = i + 1
  var arg: ptr uint8
  if trimmed[i] == cast[uint8](0):
    arg = cast[ptr uint8](0)
  else:
    arg = cast[ptr uint8](cast[int32](trimmed) + i)

  # Check for built-ins
  if strcmp(cmd_buf, cast[ptr uint8]("pwd")) == 0:
    discard builtin_pwd()
    return 1

  if strcmp(cmd_buf, cast[ptr uint8]("cd")) == 0:
    discard builtin_cd(arg)
    return 1

  if strcmp(cmd_buf, cast[ptr uint8]("env")) == 0:
    discard builtin_env()
    return 1

  if strcmp(cmd_buf, cast[ptr uint8]("history")) == 0:
    discard builtin_history()
    return 1

  return 0

# Display PSCH schema as a pretty table
proc display_schema(buffer: ptr uint8) =
  print(cast[ptr uint8]("\n┌─── Schema ───────────────────────┐\n"))
  print(cast[ptr uint8]("│ Magic:   "))
  var i: int32 = 0
  while i < 4:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer + i), 1)
    i = i + 1

  print(cast[ptr uint8]("                     │\n│ Version: "))
  print_num(cast[int32](buffer[4]))

  print(cast[ptr uint8]("                        │\n│ Fields:  "))
  print_num(cast[int32](buffer[5]))

  print(cast[ptr uint8]("                        │\n│ RecSize: "))
  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  print_num(cast[int32](rec_size_ptr[0]))
  print(cast[ptr uint8](" bytes                 │\n└──────────────────────────────────┘\n"))

# Display binary data as hex table
proc display_records(buffer: ptr uint8, rec_count: int32, rec_size: int32) =
  print(cast[ptr uint8]("\n┌─── Data ("))
  print_num(rec_count)
  print(cast[ptr uint8](" records) ───────────────┐\n"))

  var rec_idx: int32 = 0
  while rec_idx < rec_count:
    print(cast[ptr uint8]("│ ["))
    print_num(rec_idx)
    print(cast[ptr uint8]("] "))

    # Print first 12 bytes or rec_size, whichever is smaller
    var bytes_to_show: int32 = 12
    if rec_size < bytes_to_show:
      bytes_to_show = rec_size

    var byte_idx: int32 = 0
    while byte_idx < bytes_to_show:
      var byte_val: uint8 = buffer[12 + rec_idx * rec_size + byte_idx]
      var upper: uint8 = byte_val >> 4
      var lower: uint8 = byte_val & cast[uint8](15)

      var hex_upper: uint8 = cast[uint8](48 + cast[int32](upper))
      if upper > cast[uint8](9):
        hex_upper = cast[uint8](97 + cast[int32](upper) - 10)

      var hex_lower: uint8 = cast[uint8](48 + cast[int32](lower))
      if lower > cast[uint8](9):
        hex_lower = cast[uint8](97 + cast[int32](lower) - 10)

      discard syscall3(SYS_write, STDOUT, cast[int32](addr(hex_upper)), 1)
      discard syscall3(SYS_write, STDOUT, cast[int32](addr(hex_lower)), 1)
      discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)

      byte_idx = byte_idx + 1

    if rec_size > bytes_to_show:
      print(cast[ptr uint8]("..."))

    print(cast[ptr uint8](" │\n"))
    rec_idx = rec_idx + 1

  print(cast[ptr uint8]("└──────────────────────────────────┘\n"))

# Trim leading whitespace from a string, return pointer to first non-space
proc trim_start(s: ptr uint8): ptr uint8 =
  var i: int32 = 0
  while s[i] == cast[uint8](32):  # space
    i = i + 1
  return cast[ptr uint8](cast[int32](s) + i)

# Trim trailing whitespace from a string (modifies in place)
proc trim_end(s: ptr uint8) =
  var len: int32 = strlen(s)
  while len > 0:
    if s[len - 1] == cast[uint8](32):  # space
      s[len - 1] = cast[uint8](0)
      len = len - 1
    else:
      return

# Find the position of '|' in string, return -1 if not found
proc find_pipe(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    if s[i] == cast[uint8](124):  # '|'
      return i
    i = i + 1
  return -1

# Count number of commands in pipeline (number of '|' + 1)
proc count_commands(s: ptr uint8): int32 =
  var count: int32 = 1
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    if s[i] == cast[uint8](124):  # '|'
      count = count + 1
    i = i + 1
  return count

# Check if path needs ./ prefix (not absolute and not already ./)
proc needs_dot_slash(s: ptr uint8): int32 =
  if s[0] == cast[uint8](47):  # starts with '/'
    return 0
  if s[0] == cast[uint8](46):  # starts with '.'
    return 0
  return 1

# Prepend ./ to a path if needed, returns new pointer (uses dest buffer)
proc make_exec_path(src: ptr uint8, dest: ptr uint8): ptr uint8 =
  if needs_dot_slash(src) == 0:
    # Just copy as-is
    strcpy(dest, src)
    return dest
  # Prepend ./
  dest[0] = cast[uint8](46)  # '.'
  dest[1] = cast[uint8](47)  # '/'
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i + 2] = src[i]
    i = i + 1
  dest[i + 2] = cast[uint8](0)
  return dest

# Parse command string into argv array
# Returns number of arguments
# cmd_str: "bin/where 0 > 1000" -> argv = ["./bin/where", "0", ">", "1000", NULL]
# arg_buf: buffer for copying argument strings
# argv: pointer array for argument pointers (must have room for up to 16 args)
proc parse_args(cmd_str: ptr uint8, arg_buf: ptr uint8, argv: ptr int32): int32 =
  var argc: int32 = 0
  var src_pos: int32 = 0
  var dst_pos: int32 = 0

  # Skip leading whitespace
  while cmd_str[src_pos] == cast[uint8](32):
    src_pos = src_pos + 1

  while cmd_str[src_pos] != cast[uint8](0):
    # Start of argument
    var arg_start: int32 = dst_pos

    # Copy argument until space or end
    while cmd_str[src_pos] != cast[uint8](0):
      if cmd_str[src_pos] == cast[uint8](32):  # space
        break
      arg_buf[dst_pos] = cmd_str[src_pos]
      dst_pos = dst_pos + 1
      src_pos = src_pos + 1

    # Null-terminate this argument
    arg_buf[dst_pos] = cast[uint8](0)
    dst_pos = dst_pos + 1

    # Store pointer in argv
    argv[argc] = cast[int32](arg_buf) + arg_start
    argc = argc + 1

    # Skip whitespace between arguments
    while cmd_str[src_pos] == cast[uint8](32):
      src_pos = src_pos + 1

    # Safety limit
    if argc >= 15:
      break

  # Null-terminate argv
  argv[argc] = 0
  return argc

# Execute a pipeline of commands: cmd1 | cmd2 | cmd3 | ...
proc exec_pipeline(input: ptr uint8) =
  # Allocate working memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32768
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # old_brk + 0:     output buffer (8KB)
  # old_brk + 8192:  command strings storage (8KB)
  # old_brk + 16384: pipe fd array (256 bytes)
  # old_brk + 16640: pid array (256 bytes)
  # old_brk + 16896: cmd_ptrs array (256 bytes)
  # old_brk + 17152: argv arrays (2KB for 8 cmds * 16 args * 4 bytes)
  # old_brk + 19200: arg string buffers (8KB for 8 cmds * 1KB each)
  # old_brk + 27392: path buffers (2KB for 8 cmds * 256 each)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var cmd_storage: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var pipe_fds: ptr int32 = cast[ptr int32](old_brk + 16384)
  var pids: ptr int32 = cast[ptr int32](old_brk + 16640)
  var cmd_ptrs: ptr int32 = cast[ptr int32](old_brk + 16896)
  var argv_base: ptr int32 = cast[ptr int32](old_brk + 17152)
  var arg_str_base: ptr uint8 = cast[ptr uint8](old_brk + 19200)
  var path_base: ptr uint8 = cast[ptr uint8](old_brk + 27392)

  # Parse pipeline: split by '|' and store command pointers
  var num_cmds: int32 = 0
  var src_pos: int32 = 0
  var dst_pos: int32 = 0
  var cmd_start: int32 = dst_pos

  # Copy input to storage while parsing
  while input[src_pos] != cast[uint8](0):
    if input[src_pos] == cast[uint8](124):  # '|'
      # End current command
      cmd_storage[dst_pos] = cast[uint8](0)
      dst_pos = dst_pos + 1

      # Trim and store command pointer
      var trimmed: ptr uint8 = trim_start(cast[ptr uint8](cast[int32](cmd_storage) + cmd_start))
      trim_end(trimmed)
      cmd_ptrs[num_cmds] = cast[int32](trimmed)
      num_cmds = num_cmds + 1

      # Skip whitespace after |
      src_pos = src_pos + 1
      while input[src_pos] == cast[uint8](32):
        src_pos = src_pos + 1

      cmd_start = dst_pos
    else:
      cmd_storage[dst_pos] = input[src_pos]
      dst_pos = dst_pos + 1
      src_pos = src_pos + 1

  # Don't forget the last command
  cmd_storage[dst_pos] = cast[uint8](0)
  var last_trimmed: ptr uint8 = trim_start(cast[ptr uint8](cast[int32](cmd_storage) + cmd_start))
  trim_end(last_trimmed)
  cmd_ptrs[num_cmds] = cast[int32](last_trimmed)
  num_cmds = num_cmds + 1

  # If only 1 command, no pipes between commands needed, but still pipe to parent
  # For N commands, we need N pipes total:
  # - N-1 pipes between commands
  # - 1 pipe from last command to parent (for PSCH detection)

  # Create all pipes: pipe_fds[i*2] = read, pipe_fds[i*2+1] = write
  var num_pipes: int32 = num_cmds  # N pipes for N commands
  var i: int32 = 0
  while i < num_pipes:
    var pipe_result: int32 = syscall1(SYS_pipe, cast[int32](addr(pipe_fds[i * 2])))
    if pipe_result != 0:
      print_err(cast[ptr uint8]("Error: pipe() failed\n"))
      return
    i = i + 1

  # Fork all children
  i = 0
  while i < num_cmds:
    var pid: int32 = syscall1(SYS_fork, 0)

    if pid == 0:
      # Child process

      # Set up stdin: if not first command, read from previous pipe
      if i > 0:
        discard syscall2(SYS_dup2, pipe_fds[(i - 1) * 2], STDIN)

      # Set up stdout: write to our pipe
      discard syscall2(SYS_dup2, pipe_fds[i * 2 + 1], STDOUT)

      # Close all pipe fds
      var j: int32 = 0
      while j < num_pipes * 2:
        discard syscall1(SYS_close, pipe_fds[j])
        j = j + 1

      # Parse arguments from command string
      var arg_buf: ptr uint8 = cast[ptr uint8](cast[int32](arg_str_base) + i * 1024)
      var argv: ptr int32 = cast[ptr int32](cast[int32](argv_base) + i * 64)  # 16 args * 4 bytes
      var argc: int32 = parse_args(cast[ptr uint8](cmd_ptrs[i]), arg_buf, argv)

      # Build exec path from first argument (use PATH resolution)
      var path_buf: ptr uint8 = cast[ptr uint8](cast[int32](path_base) + i * 256)
      var first_arg: ptr uint8 = cast[ptr uint8](argv[0])
      var exec_path: ptr uint8 = resolve_path(first_arg, path_buf)

      # Update argv[0] to use the exec path
      argv[0] = cast[int32](exec_path)

      # Exec!
      discard syscall3(SYS_execve, cast[int32](exec_path), cast[int32](argv), 0)

      # Exec failed
      print_err(cast[ptr uint8]("Error: exec failed: "))
      print_err(exec_path)
      print_err(cast[ptr uint8]("\n"))
      discard syscall1(SYS_exit, 1)

    # Parent: store pid
    pids[i] = pid
    i = i + 1

  # Parent: close all pipe ends except the read end of the last pipe
  i = 0
  while i < num_pipes:
    # Close write end of all pipes
    discard syscall1(SYS_close, pipe_fds[i * 2 + 1])
    # Close read end of all but the last pipe
    if i < num_pipes - 1:
      discard syscall1(SYS_close, pipe_fds[i * 2])
    i = i + 1

  # Read from the last pipe (final output)
  var final_read_fd: int32 = pipe_fds[(num_pipes - 1) * 2]

  # Read magic bytes to check if it's PSCH format
  var n: int32 = syscall3(SYS_read, final_read_fd, cast[int32](buffer), 4)

  if n == 4:
    # Check for "PSCH" magic
    if buffer[0] == cast[uint8](80):  # 'P'
      if buffer[1] == cast[uint8](83):  # 'S'
        if buffer[2] == cast[uint8](67):  # 'C'
          if buffer[3] == cast[uint8](72):  # 'H'
            # It's PSCH format! Read the rest of schema
            n = syscall3(SYS_read, final_read_fd, cast[int32](buffer + 4), 8)

            display_schema(buffer)

            var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
            var rec_size: int32 = cast[int32](rec_size_ptr[0])
            var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
            var rec_count: int32 = rec_count_ptr[0]

            var total_size: int32 = rec_count * rec_size
            if total_size > 8000:
              total_size = 8000
            n = syscall3(SYS_read, final_read_fd, cast[int32](buffer + 12), total_size)

            display_records(buffer, rec_count, rec_size)

            discard syscall1(SYS_close, final_read_fd)

            # Wait for all children
            i = 0
            while i < num_cmds:
              var status: int32 = 0
              discard syscall3(SYS_waitpid, pids[i], cast[int32](addr(status)), 0)
              i = i + 1
            return

  # Not PSCH format - pass through raw output
  if n > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer), n)

  # Read and output remaining data
  n = syscall3(SYS_read, final_read_fd, cast[int32](buffer), 8000)
  while n > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer), n)
    n = syscall3(SYS_read, final_read_fd, cast[int32](buffer), 8000)

  discard syscall1(SYS_close, final_read_fd)

  # Wait for all children
  i = 0
  while i < num_cmds:
    var status: int32 = 0
    discard syscall3(SYS_waitpid, pids[i], cast[int32](addr(status)), 0)
    i = i + 1

# Main REPL
proc main() =
  # Welcome banner
  print(cast[ptr uint8]("\n"))
  print(cast[ptr uint8]("╔════════════════════════════════════════════════╗\n"))
  print(cast[ptr uint8]("║  PoodillionOS Shell - Type-Aware Data Shell   ║\n"))
  print(cast[ptr uint8]("║                                                ║\n"))
  print(cast[ptr uint8]("║  • Type-safe binary pipelines                 ║\n"))
  print(cast[ptr uint8]("║  • Automatic schema detection                 ║\n"))
  print(cast[ptr uint8]("║  • Pretty table formatting                    ║\n"))
  print(cast[ptr uint8]("║                                                ║\n"))
  print(cast[ptr uint8]("║  Try: bin/ps | bin/where | bin/select         ║\n"))
  print(cast[ptr uint8]("╚════════════════════════════════════════════════╝\n"))
  print(cast[ptr uint8]("\n"))

  # Allocate ALL memory upfront - never use brk again!
  var initial_brk: int32 = syscall1(SYS_brk, 0)
  var total_mem: int32 = initial_brk + 65536  # 64KB total
  discard syscall1(SYS_brk, total_mem)

  # Memory layout:
  # initial_brk + 0:     input buffer (1KB)
  # initial_brk + 1024:  g_cwd_buf (512 bytes)
  # initial_brk + 1536:  g_prev_dir (512 bytes)
  # initial_brk + 2048:  g_home_dir (512 bytes)
  # initial_brk + 2560:  g_history array (20 pointers * 4 = 80 bytes)
  # initial_brk + 2640:  g_history_storage (20 commands * 256 = 5120 bytes)
  # initial_brk + 7760:  prompt buffer (512 bytes)
  # initial_brk + 8272:  cmd_buf for parsing (256 bytes)
  # initial_brk + 8528:  reserved for future builtins (56KB)

  var input: ptr uint8 = cast[ptr uint8](initial_brk)
  g_cwd_buf = cast[ptr uint8](initial_brk + 1024)
  g_prev_dir = cast[ptr uint8](initial_brk + 1536)
  g_home_dir = cast[ptr uint8](initial_brk + 2048)
  g_history = cast[ptr int32](initial_brk + 2560)
  g_history_storage = cast[ptr uint8](initial_brk + 2640)
  var prompt_buf: ptr uint8 = cast[ptr uint8](initial_brk + 7760)
  var cmd_buf: ptr uint8 = cast[ptr uint8](initial_brk + 8272)

  # Save the brk limit - built-ins can use memory starting here
  var builtin_scratch: ptr uint8 = cast[ptr uint8](initial_brk + 8528)
  var pipeline_brk_start: int32 = initial_brk + 8528

  # Initialize previous directory to empty
  g_prev_dir[0] = cast[uint8](0)

  # Get HOME from environment (use /root as default)
  strcpy(g_home_dir, cast[ptr uint8]("/root"))

  # Try to read HOME from /proc/self/environ
  var env_fd: int32 = syscall3(SYS_open, cast[int32]("/proc/self/environ"), 0, 0)
  if env_fd >= 0:
    var env_buf_brk: int32 = syscall1(SYS_brk, 0)
    var env_buf_new: int32 = env_buf_brk + 4096
    discard syscall1(SYS_brk, env_buf_new)
    var env_buf: ptr uint8 = cast[ptr uint8](env_buf_brk)

    var env_n: int32 = syscall3(SYS_read, env_fd, cast[int32](env_buf), 4000)
    discard syscall1(SYS_close, env_fd)

    if env_n > 0:
      # Search for HOME= in environment
      var i: int32 = 0
      while i < env_n:
        # Check if this entry starts with "HOME="
        if i + 5 < env_n:
          if env_buf[i] == cast[uint8](72):      # 'H'
            if env_buf[i+1] == cast[uint8](79):  # 'O'
              if env_buf[i+2] == cast[uint8](77):  # 'M'
                if env_buf[i+3] == cast[uint8](69):  # 'E'
                  if env_buf[i+4] == cast[uint8](61):  # '='
                    # Found HOME=, copy the value
                    var j: int32 = 0
                    var k: int32 = i + 5
                    while k < env_n:
                      if env_buf[k] == cast[uint8](0):
                        break
                      g_home_dir[j] = env_buf[k]
                      j = j + 1
                      k = k + 1
                    g_home_dir[j] = cast[uint8](0)
        # Skip to next entry
        while i < env_n:
          if env_buf[i] == cast[uint8](0):
            i = i + 1
            break
          i = i + 1

  # REPL loop
  var running: int32 = 1
  while running != 0:
    # Build prompt with current directory (but keep it simple for now)
    print(cast[ptr uint8]("psh> "))

    # Read command
    var n: int32 = syscall3(SYS_read, STDIN, cast[int32](input), 1024)
    if n <= 0:
      running = 0

    if running != 0:
      # Remove trailing newline
      if n > 0:
        if input[n - 1] == cast[uint8](10):
          input[n - 1] = cast[uint8](0)
          n = n - 1
        else:
          input[n] = cast[uint8](0)

      # Check for empty input
      if n > 0:
        # Check for exit/quit
        if strcmp(input, cast[ptr uint8]("exit")) == 0:
          running = 0
        if strcmp(input, cast[ptr uint8]("quit")) == 0:
          running = 0

        # Execute command if not exiting
        if running != 0:
          # Add to history
          add_to_history(input)

          # Try built-in commands first
          var trimmed: ptr uint8 = trim_start(input)
          trim_end(trimmed)
          var is_builtin: int32 = try_builtin_impl(trimmed, cmd_buf)
          if is_builtin == 0:
            # Not a built-in, execute as pipeline
            exec_pipeline(input)

  println(cast[ptr uint8]("Goodbye!"))
  discard syscall1(SYS_exit, 0)
