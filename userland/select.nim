# select - project specific fields from structured data stream
# Usage: ps | select <field_indices>
# Example: ps | select 0  (extract only pid field)

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
  # TODO: Parse command-line arguments
  # For now, hardcode: select field 0 only (pid)
  var select_count: int32 = 1
  var select_field0: int32 = 0  # Which field to extract

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
  var old_field_count: uint8 = buffer[5]

  # Record size: 2 bytes
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 6), 2)
  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  var old_rec_size: int32 = cast[int32](rec_size_ptr[0])

  # Read record count: 4 bytes
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 8), 4)
  var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
  var rec_count: int32 = rec_count_ptr[0]

  # Calculate new schema
  # Assume all fields are int32 (4 bytes each)
  var new_field_count: uint8 = cast[uint8](select_count)
  var new_rec_size: uint16 = cast[uint16](select_count * 4)

  # Write new schema header
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer), 4)  # Magic (PSCH)
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer + 4), 1)  # Version
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(new_field_count)), 1)  # New field count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(new_rec_size)), 2)  # New record size
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(rec_count)), 4)  # Same record count

  # Process records
  var i: int32 = 0
  while i < rec_count:
    # Read one record
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), old_rec_size)
    if n <= 0:
      i = rec_count  # Exit loop

    if n > 0:
      # Extract selected field (assume int32 at offset = field_index * 4)
      var field_offset: int32 = select_field0 * 4
      var field_ptr: ptr int32 = cast[ptr int32](buffer + 12 + field_offset)
      var field_val: int32 = field_ptr[0]

      # Write selected field
      discard syscall3(SYS_write, STDOUT, cast[int32](addr(field_val)), 4)

    i = i + 1

  discard syscall1(SYS_exit, 0)
