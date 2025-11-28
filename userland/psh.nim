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

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

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

      # Build exec path from first argument (prepend ./ if needed)
      var path_buf: ptr uint8 = cast[ptr uint8](cast[int32](path_base) + i * 256)
      var first_arg: ptr uint8 = cast[ptr uint8](argv[0])
      var exec_path: ptr uint8 = make_exec_path(first_arg, path_buf)

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

  # Allocate input buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var input: ptr uint8 = cast[ptr uint8](old_brk)

  # REPL loop
  var running: int32 = 1
  while running != 0:
    # Display prompt
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
          exec_pipeline(input)

  println(cast[ptr uint8]("Goodbye!"))
  discard syscall1(SYS_exit, 0)
