# xxd - Hex dump utility
# Usage: xxd [FILE]
#        xxd -r  (reverse: hex to binary)
#        xxd -i  (C include style)
# Output format: OFFSET: HEX HEX HEX HEX  ASCII
# 16 bytes per line

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

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

# Print hex digit (0-15 -> '0'-'9', 'a'-'f')
proc print_hex_digit(n: int32) =
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  if n < 10:
    buf[0] = cast[uint8](48 + n)
  else:
    buf[0] = cast[uint8](97 + n - 10)

  discard syscall3(SYS_write, STDOUT, cast[int32](buf), 1)

# Print byte as 2-digit hex
proc print_hex_byte(b: uint8) =
  var high: int32 = cast[int32](b) / 16
  var low: int32 = cast[int32](b) % 16
  print_hex_digit(high)
  print_hex_digit(low)

# Print 32-bit offset as 8-digit hex (00000000 format)
proc print_offset(offset: int32) =
  var temp: int32 = offset

  # Print 8 hex digits (most significant first)
  # Digit 7 (bits 28-31)
  print_hex_digit((temp / 268435456) % 16)
  # Digit 6 (bits 24-27)
  print_hex_digit((temp / 16777216) % 16)
  # Digit 5 (bits 20-23)
  print_hex_digit((temp / 1048576) % 16)
  # Digit 4 (bits 16-19)
  print_hex_digit((temp / 65536) % 16)
  # Digit 3 (bits 12-15)
  print_hex_digit((temp / 4096) % 16)
  # Digit 2 (bits 8-11)
  print_hex_digit((temp / 256) % 16)
  # Digit 1 (bits 4-7)
  print_hex_digit((temp / 16) % 16)
  # Digit 0 (bits 0-3)
  print_hex_digit(temp % 16)

# Print character (printable or '.')
proc print_ascii_char(c: uint8) =
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  if c >= cast[uint8](32) and c < cast[uint8](127):
    buf[0] = c
  else:
    buf[0] = cast[uint8](46)  # '.'

  discard syscall3(SYS_write, STDOUT, cast[int32](buf), 1)

# Check if string starts with prefix
proc starts_with(s: ptr uint8, prefix: ptr uint8): int32 =
  var i: int32 = 0
  while prefix[i] != cast[uint8](0):
    if s[i] != prefix[i]:
      return 0
    i = i + 1
  return 1

# Parse hex digit ('0'-'9', 'a'-'f', 'A'-'F' -> 0-15)
proc parse_hex_digit(c: uint8): int32 =
  if c >= cast[uint8](48) and c <= cast[uint8](57):  # '0'-'9'
    return cast[int32](c) - 48
  if c >= cast[uint8](97) and c <= cast[uint8](102):  # 'a'-'f'
    return cast[int32](c) - 97 + 10
  if c >= cast[uint8](65) and c <= cast[uint8](70):  # 'A'-'F'
    return cast[int32](c) - 65 + 10
  return -1

# Reverse mode: convert hex to binary
proc reverse_mode(fd: int32) =
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var out_buf: ptr uint8 = cast[ptr uint8](old_brk + 4096)

  var running: int32 = 1
  while running != 0:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
    if n <= 0:
      running = 0
      break

    # Parse hex pairs and output bytes
    var i: int32 = 0
    var out_pos: int32 = 0
    while i < n:
      var c: uint8 = buffer[i]

      # Skip non-hex characters (whitespace, colons, etc)
      var digit1: int32 = parse_hex_digit(c)
      if digit1 >= 0:
        # Look for second digit
        i = i + 1
        if i < n:
          var digit2: int32 = parse_hex_digit(buffer[i])
          if digit2 >= 0:
            var byte_val: uint8 = cast[uint8](digit1 * 16 + digit2)
            out_buf[out_pos] = byte_val
            out_pos = out_pos + 1

      i = i + 1

    # Write output
    if out_pos > 0:
      discard syscall3(SYS_write, STDOUT, cast[int32](out_buf), out_pos)

# C include mode: output as C array
proc c_include_mode(fd: int32, filename: ptr uint8) =
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Print array declaration
  print(cast[ptr uint8]("unsigned char "))
  if filename != cast[ptr uint8](0):
    # Convert filename to valid C identifier (replace . with _)
    var i: int32 = 0
    while filename[i] != cast[uint8](0):
      if filename[i] == cast[uint8](46):  # '.'
        discard syscall3(SYS_write, STDOUT, cast[int32]("_"), 1)
      else:
        discard syscall3(SYS_write, STDOUT, cast[int32](filename + i), 1)
      i = i + 1
  else:
    print(cast[ptr uint8]("stdin"))
  print(cast[ptr uint8]("[] = {\n  "))

  var total: int32 = 0
  var running: int32 = 1
  var first: int32 = 1

  while running != 0:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
    if n <= 0:
      running = 0
      break

    var i: int32 = 0
    while i < n:
      if first == 0:
        print(cast[ptr uint8](", "))
      first = 0

      # Print as 0xNN
      print(cast[ptr uint8]("0x"))
      print_hex_byte(buffer[i])

      total = total + 1
      if total % 12 == 0:
        print(cast[ptr uint8]("\n  "))

      i = i + 1

  print(cast[ptr uint8]("\n};\n"))
  print(cast[ptr uint8]("unsigned int "))
  if filename != cast[ptr uint8](0):
    var i: int32 = 0
    while filename[i] != cast[uint8](0):
      if filename[i] == cast[uint8](46):
        discard syscall3(SYS_write, STDOUT, cast[int32]("_"), 1)
      else:
        discard syscall3(SYS_write, STDOUT, cast[int32](filename + i), 1)
      i = i + 1
  else:
    print(cast[ptr uint8]("stdin"))
  print(cast[ptr uint8]("_len = "))

  # Print length
  var len: int32 = total
  var old_brk2: int32 = syscall1(SYS_brk, 0)
  var new_brk2: int32 = old_brk2 + 32
  discard syscall1(SYS_brk, new_brk2)
  var num_buf: ptr uint8 = cast[ptr uint8](old_brk2)
  var pos: int32 = 0

  if len == 0:
    num_buf[0] = cast[uint8](48)
    pos = 1
  else:
    while len > 0:
      num_buf[pos] = cast[uint8](48 + (len % 10))
      len = len / 10
      pos = pos + 1

  # Reverse and print
  var j: int32 = pos - 1
  while j >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](num_buf + j), 1)
    j = j - 1

  print(cast[ptr uint8](";\n"))

# Normal hex dump mode
proc normal_mode(fd: int32) =
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var line_buf: ptr uint8 = cast[ptr uint8](old_brk + 4096)

  var offset: int32 = 0
  var running: int32 = 1

  while running != 0:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
    if n <= 0:
      running = 0
      break

    var pos: int32 = 0
    while pos < n:
      var line_pos: int32 = pos % 16

      # Print offset at start of line
      if line_pos == 0:
        print_offset(offset + pos)
        print(cast[ptr uint8](": "))

      # Store byte in line buffer
      line_buf[line_pos] = buffer[pos]

      # Print hex byte
      print_hex_byte(buffer[pos])
      discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)

      # Add extra space after 8 bytes
      if line_pos == 7:
        discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)

      # At end of line or end of data, print ASCII
      if line_pos == 15 or pos + 1 >= n:
        var actual_len: int32 = line_pos + 1

        # Pad if incomplete line
        if actual_len < 16:
          var pad: int32 = actual_len
          while pad < 16:
            print(cast[ptr uint8]("   "))
            if pad == 7:
              discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
            pad = pad + 1

        # Print ASCII representation
        discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
        var k: int32 = 0
        while k < actual_len:
          print_ascii_char(line_buf[k])
          k = k + 1

        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

      pos = pos + 1

    offset = offset + n

proc main() =
  var argc: int32 = get_argc()
  var fd: int32 = STDIN
  var filename: ptr uint8 = cast[ptr uint8](0)
  var reverse: int32 = 0
  var c_include: int32 = 0

  # Parse arguments
  var i: int32 = 1
  while i < argc:
    var arg: ptr uint8 = get_argv(i)

    if arg[0] == cast[uint8](45):  # '-'
      if arg[1] == cast[uint8](114):  # 'r'
        reverse = 1
      else:
        if arg[1] == cast[uint8](105):  # 'i'
          c_include = 1
    else:
      filename = arg

    i = i + 1

  # Open file if provided
  if filename != cast[ptr uint8](0):
    fd = syscall2(SYS_open, cast[int32](filename), O_RDONLY)
    if fd < 0:
      print_err(cast[ptr uint8]("xxd: cannot open file\n"))
      discard syscall1(SYS_exit, 1)

  # Run appropriate mode
  if reverse != 0:
    reverse_mode(fd)
  else:
    if c_include != 0:
      c_include_mode(fd, filename)
    else:
      normal_mode(fd)

  if fd != STDIN:
    discard syscall1(SYS_close, fd)

  discard syscall1(SYS_exit, 0)
