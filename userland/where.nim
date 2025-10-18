# where - filter structured data streams by predicate
# Usage: ps | where <field_index> <operator> <value>
# Example: ps | where 0 > 100  (filter pid > 100)

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# Simple print for error messages
proc print_err(msg: ptr uint8) =
  var i: int32 = 0
  while msg[i] != cast[uint8](0):
    i = i + 1
  discard syscall3(SYS_write, STDERR, cast[int32](msg), i)

proc main() =
  # TODO: Parse command-line arguments
  # For now, hardcode: field 0, operator >, value 1
  var filter_field: int32 = 0
  var filter_op: int32 = 1  # 1 = >, 2 = <, 3 = ==, 4 = !=, 5 = >=, 6 = <=
  var filter_value: int32 = 1

  # Allocate buffer - need room for schema (12 bytes) + records + record buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384  # 16KB total
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Record buffer starts after schema space (12 bytes) and input record space
  var rec_buffer: ptr uint8 = cast[ptr uint8](old_brk + 4096)

  # Read schema header
  # Magic: 4 bytes
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 4)
  if n != 4:
    print_err(cast[ptr uint8]("Error: No schema header\n"))
    discard syscall1(SYS_exit, 1)

  # Version: 1 byte
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 4), 1)
  var version: uint8 = buffer[4]

  # Field count: 1 byte
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 5), 1)
  var field_count: uint8 = buffer[5]

  # Record size: 2 bytes
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 6), 2)
  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  var rec_size: int32 = cast[int32](rec_size_ptr[0])

  # Read record count: 4 bytes
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 8), 4)
  var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
  var rec_count: int32 = rec_count_ptr[0]

  # First pass: Read all records, buffer matching ones, count them
  var match_count: int32 = 0
  var rec_buf_offset: int32 = 0
  var i: int32 = 0

  while i < rec_count:
    # Read one record
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), rec_size)
    if n <= 0:
      i = rec_count  # Exit loop

    if n > 0:
      # Extract field value (assuming field is int32 at offset = field_index * 4)
      var field_offset: int32 = filter_field * 4
      var field_ptr: ptr int32 = cast[ptr int32](buffer + 12 + field_offset)
      var field_val: int32 = field_ptr[0]

      # Apply filter
      var match: int32 = 0
      if filter_op == 1:  # >
        if field_val > filter_value:
          match = 1
      if filter_op == 2:  # <
        if field_val < filter_value:
          match = 1
      if filter_op == 3:  # ==
        if field_val == filter_value:
          match = 1
      if filter_op == 4:  # !=
        if field_val != filter_value:
          match = 1
      if filter_op == 5:  # >=
        if field_val >= filter_value:
          match = 1
      if filter_op == 6:  # <=
        if field_val <= filter_value:
          match = 1

      # Buffer record if it matches
      if match != 0:
        # Copy record to buffer
        var j: int32 = 0
        while j < rec_size:
          rec_buffer[rec_buf_offset + j] = buffer[12 + j]
          j = j + 1
        rec_buf_offset = rec_buf_offset + rec_size
        match_count = match_count + 1

    # Increment loop counter
    i = i + 1

  # Write schema header to output
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer), 8)

  # Write ACTUAL filtered record count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(match_count)), 4)

  # Write all buffered matching records
  if match_count > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](rec_buffer), rec_buf_offset)

  discard syscall1(SYS_exit, 0)
