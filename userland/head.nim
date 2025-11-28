# head - output first N records from structured data stream
# Usage: ps | head [N]
# Default N = 10

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] >= cast[uint8](48):
    if s[i] > cast[uint8](57):
      break
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

proc main() =
  var argc: int32 = get_argc()
  var take_count: int32 = 10  # Default

  if argc >= 2:
    var arg1: ptr uint8 = get_argv(1)
    take_count = parse_int(arg1)
    if take_count <= 0:
      take_count = 10

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 65536
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read schema header (8 bytes)
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 8)
  if n != 8:
    print_err(cast[ptr uint8]("Error: No schema header\n"))
    discard syscall1(SYS_exit, 1)

  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  var rec_size: int32 = cast[int32](rec_size_ptr[0])

  # Read record count
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 8), 4)
  var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
  var rec_count: int32 = rec_count_ptr[0]

  # Write schema header
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer), 8)

  # Calculate output count
  var output_count: int32 = take_count
  if rec_count < take_count:
    output_count = rec_count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(output_count)), 4)

  # Read and output first N records
  var i: int32 = 0
  while i < rec_count:
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), rec_size)
    if n <= 0:
      break
    if i < take_count:
      discard syscall3(SYS_write, STDOUT, cast[int32](buffer + 12), rec_size)
    i = i + 1

  discard syscall1(SYS_exit, 0)
