# head - output first N records from structured data stream
# Usage: ps | head
# For now, N is hardcoded to 1

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print_err(msg: ptr uint8) =
  var i: int32 = 0
  while msg[i] != cast[uint8](0):
    i = i + 1
  discard syscall3(SYS_write, STDERR, cast[int32](msg), i)

proc main() =
  # Hardcoded: take first N records
  var take_count: int32 = 1

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read schema header
  # Magic: 4 bytes
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 4)
  if n != 4:
    print_err(cast[ptr uint8]("Error: No schema header\n"))
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

  # Write schema header to output
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer), 8)

  # Write updated record count (min of original count and take_count)
  var output_count: int32 = take_count
  if rec_count < take_count:
    output_count = rec_count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(output_count)), 4)

  # Read and output first N records
  var i: int32 = 0
  while i < rec_count:
    # Read one record
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), rec_size)
    if n <= 0:
      i = rec_count  # Exit loop

    if n > 0:
      # Only write if we haven't reached take_count
      if i < take_count:
        discard syscall3(SYS_write, STDOUT, cast[int32](buffer + 12), rec_size)

    i = i + 1

  discard syscall1(SYS_exit, 0)
