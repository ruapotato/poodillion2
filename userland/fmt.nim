# fmt - format structured data for human display
# Usage: ps | sort 3 desc | head 10 | fmt

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print(s: ptr uint8) =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

proc print_char(c: uint8) =
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(c)), 1)

proc print_int(n: int32) =
  # Print integer (simple version, no padding)
  if n == 0:
    print_char(cast[uint8](48))
    return

  # Count digits
  var temp: int32 = n
  var divisor: int32 = 1
  while temp >= 10:
    divisor = divisor * 10
    temp = temp / 10

  # Print digits from most significant to least
  temp = n
  while divisor > 0:
    var digit: int32 = temp / divisor
    print_char(cast[uint8](48 + digit))
    temp = temp % divisor
    divisor = divisor / 10

proc print_int_padded(n: int32, width: int32) =
  # Count digits first
  var temp: int32 = n
  var digits: int32 = 0
  if n == 0:
    digits = 1
  else:
    while temp > 0:
      digits = digits + 1
      temp = temp / 10

  # Print leading spaces
  var spaces: int32 = width - digits
  while spaces > 0:
    print_char(cast[uint8](32))
    spaces = spaces - 1

  # Print the number
  print_int(n)

proc print_str_padded(s: ptr uint8, max_len: int32) =
  var i: int32 = 0
  while i < max_len:
    if s[i] == cast[uint8](0):
      break
    print_char(s[i])
    i = i + 1
  # Pad with spaces
  while i < max_len:
    print_char(cast[uint8](32))
    i = i + 1

proc main() =
  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 65536
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read schema header (8 bytes)
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 8)
  if n != 8:
    print(cast[ptr uint8]("Error: No schema header\n"))
    discard syscall1(SYS_exit, 1)

  var field_count: int32 = cast[int32](buffer[5])
  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  var rec_size: int32 = cast[int32](rec_size_ptr[0])

  # Read record count
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 8), 4)
  var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
  var rec_count: int32 = rec_count_ptr[0]

  # Print header line for 5-field ps schema
  if field_count == 5:
    print(cast[ptr uint8]("   PID   PPID S   RSS KB  Name\n"))
    print(cast[ptr uint8]("------ ------ - -------- --------------------------------\n"))

  # Read and format each record
  var i: int32 = 0
  while i < rec_count:
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), rec_size)
    if n <= 0:
      break

    # For 5-field schema (ps output)
    if field_count == 5:
      var rec: ptr uint8 = buffer + 12

      # Field 0: pid (4 bytes at offset 0)
      var pid_ptr: ptr int32 = cast[ptr int32](rec)
      var pid: int32 = pid_ptr[0]
      print_int_padded(pid, 6)
      print_char(cast[uint8](32))

      # Field 1: ppid (4 bytes at offset 4)
      var ppid_ptr: ptr int32 = cast[ptr int32](cast[int32](rec) + 4)
      var ppid: int32 = ppid_ptr[0]
      print_int_padded(ppid, 6)
      print_char(cast[uint8](32))

      # Field 2: state (1 byte at offset 8)
      var state: uint8 = rec[8]
      print_char(state)
      print_char(cast[uint8](32))

      # Field 3: rss (4 bytes at offset 12)
      var rss_ptr: ptr int32 = cast[ptr int32](cast[int32](rec) + 12)
      var rss: int32 = rss_ptr[0]
      print_int_padded(rss, 8)
      print_char(cast[uint8](32))
      print_char(cast[uint8](32))

      # Field 4: name (32 bytes at offset 16)
      var name: ptr uint8 = cast[ptr uint8](cast[int32](rec) + 16)
      print_str_padded(name, 32)
      print_char(cast[uint8](10))  # newline
    else:
      # Generic output for other schemas
      var j: int32 = 0
      while j < rec_size:
        var byte_val: uint8 = buffer[12 + j]
        if byte_val >= cast[uint8](32):
          if byte_val < cast[uint8](127):
            print_char(byte_val)
        j = j + 1
      print_char(cast[uint8](10))

    i = i + 1

  discard syscall1(SYS_exit, 0)
