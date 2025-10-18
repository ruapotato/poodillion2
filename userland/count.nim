# count - count records in structured data stream
# Usage: ps | count
# Output: text showing record count

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print(msg: ptr uint8) =
  var i: int32 = 0
  while msg[i] != cast[uint8](0):
    i = i + 1
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), i)

proc print_number(n: int32) =
  # Convert number to string and print
  # Simple approach: divide by powers of 10
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  # Allocate small buffer for digits
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Extract digits (reverse order)
  var temp: int32 = n
  var count: int32 = 0
  while temp > 0:
    var digit: int32 = temp % 10
    buffer[count] = cast[uint8](48 + digit)  # '0' = 48
    count = count + 1
    temp = temp / 10

  # Print digits in correct order (reverse)
  var i: int32 = count - 1
  while i >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(buffer[i])), 1)
    i = i - 1

proc main() =
  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read schema header
  # Magic: 4 bytes
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 4)
  if n != 4:
    print(cast[ptr uint8]("Error: No schema header\n"))
    discard syscall1(SYS_exit, 1)

  # Version: 1 byte
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 4), 1)

  # Field count: 1 byte
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 5), 1)

  # Record size: 2 bytes
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 6), 2)
  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  var rec_size: int32 = cast[int32](rec_size_ptr[0])

  # Read record count: 4 bytes
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 8), 4)
  var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
  var rec_count: int32 = rec_count_ptr[0]

  # Consume all records (read and discard)
  var actual_count: int32 = 0
  var i: int32 = 0
  while i < rec_count:
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), rec_size)
    if n > 0:
      actual_count = actual_count + 1
    i = i + 1

  # Print result
  print(cast[ptr uint8]("Record count: "))
  print_number(actual_count)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
