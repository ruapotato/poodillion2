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

# Execute a single command (no pipes yet)
proc exec_command(cmd: ptr uint8) =
  # Allocate buffer for reading output
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Create pipe
  var pipe_fds: ptr int32 = cast[ptr int32](old_brk + 8192)
  var pipe_result: int32 = syscall1(SYS_pipe, cast[int32](pipe_fds))
  if pipe_result != 0:
    print_err(cast[ptr uint8]("Error: pipe() failed\n"))
    return

  var pipe_read: int32 = pipe_fds[0]
  var pipe_write: int32 = pipe_fds[1]

  # Fork child process
  var pid: int32 = syscall1(SYS_fork, 0)

  if pid == 0:
    # Child: redirect stdout to pipe and exec command
    discard syscall2(SYS_dup2, pipe_write, STDOUT)
    discard syscall1(SYS_close, pipe_read)
    discard syscall1(SYS_close, pipe_write)

    # Build argv
    var argv: ptr int32 = cast[ptr int32](old_brk + 4096)
    argv[0] = cast[int32](cmd)
    argv[1] = 0

    # Exec command
    discard syscall3(SYS_execve, cast[int32](cmd), cast[int32](argv), 0)

    # If exec fails
    print_err(cast[ptr uint8]("Error: exec failed\n"))
    discard syscall1(SYS_exit, 1)

  if pid > 0:
    # Parent: close write end, read from pipe
    discard syscall1(SYS_close, pipe_write)

    # Read magic bytes to check if it's PSCH format
    var n: int32 = syscall3(SYS_read, pipe_read, cast[int32](buffer), 4)

    if n == 4:
      # Check for "PSCH" magic
      if buffer[0] == cast[uint8](80):  # 'P'
        if buffer[1] == cast[uint8](83):  # 'S'
          if buffer[2] == cast[uint8](67):  # 'C'
            if buffer[3] == cast[uint8](72):  # 'H'
              # It's PSCH format! Read the rest of schema (8 more bytes)
              n = syscall3(SYS_read, pipe_read, cast[int32](buffer + 4), 8)

              # Display schema
              display_schema(buffer)

              # Get record info from header
              var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
              var rec_size: int32 = cast[int32](rec_size_ptr[0])

              # Record count is already in buffer at offset 8
              var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
              var rec_count: int32 = rec_count_ptr[0]

              # Read all records (they start immediately after the header)
              var total_size: int32 = rec_count * rec_size
              if total_size > 8000:
                total_size = 8000  # Limit display
              n = syscall3(SYS_read, pipe_read, cast[int32](buffer + 12), total_size)

              # Display as table (buffer is already in correct format)
              display_records(buffer, rec_count, rec_size)

              # Close pipe
              discard syscall1(SYS_close, pipe_read)

              # Wait for child
              var status: int32 = 0
              discard syscall3(SYS_waitpid, pid, cast[int32](addr(status)), 0)

              return

    # Not PSCH format or read failed - just pass through any remaining data
    discard syscall1(SYS_close, pipe_read)

    # Wait for child
    var status: int32 = 0
    discard syscall3(SYS_waitpid, pid, cast[int32](addr(status)), 0)

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
          exec_command(input)

  println(cast[ptr uint8]("Goodbye!"))
  discard syscall1(SYS_exit, 0)
