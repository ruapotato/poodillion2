# where - filter structured data streams by predicate
# Usage: ps | where <field_index> <operator> <value>
# Example: ps | where 0 > 100  (filter pid > 100)
# Operators: > < = != >= <=

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

# Parse integer from string
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  var neg: int32 = 0
  if s[i] == cast[uint8](45):  # '-'
    neg = 1
    i = i + 1
  while s[i] >= cast[uint8](48):
    if s[i] > cast[uint8](57):
      break
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  if neg == 1:
    result = 0 - result
  return result

# Parse operator: returns 1=>, 2=<, 3===, 4=!=, 5=>=, 6=<=
proc parse_op(s: ptr uint8): int32 =
  if s[0] == cast[uint8](62):  # '>'
    if s[1] == cast[uint8](61):  # '>='
      return 5
    return 1
  if s[0] == cast[uint8](60):  # '<'
    if s[1] == cast[uint8](61):  # '<='
      return 6
    return 2
  if s[0] == cast[uint8](61):  # '=' or '=='
    return 3
  if s[0] == cast[uint8](33):  # '!='
    return 4
  return 0  # unknown

proc main() =
  var argc: int32 = get_argc()

  # Default filter: field 0 > 0 (pass all)
  var filter_field: int32 = 0
  var filter_op: int32 = 1  # 1=>, 2=<, 3===, 4=!=, 5=>=, 6=<=
  var filter_value: int32 = 0

  # Parse arguments: where FIELD OP VALUE
  if argc >= 4:
    var arg1: ptr uint8 = get_argv(1)  # field index
    var arg2: ptr uint8 = get_argv(2)  # operator
    var arg3: ptr uint8 = get_argv(3)  # value
    filter_field = parse_int(arg1)
    filter_op = parse_op(arg2)
    filter_value = parse_int(arg3)
  else:
    if argc >= 2:
      # Just field index, default to > 0
      var arg1: ptr uint8 = get_argv(1)
      filter_field = parse_int(arg1)

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 131072  # 128KB for large datasets
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var rec_buffer: ptr uint8 = cast[ptr uint8](old_brk + 8192)

  # Read schema header (8 bytes)
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 8)
  if n != 8:
    print_err(cast[ptr uint8]("Error: No schema header\n"))
    discard syscall1(SYS_exit, 1)

  # Check magic
  if buffer[0] != cast[uint8](80):  # 'P'
    print_err(cast[ptr uint8]("Error: Invalid magic\n"))
    discard syscall1(SYS_exit, 1)

  var rec_size_ptr: ptr uint16 = cast[ptr uint16](buffer + 6)
  var rec_size: int32 = cast[int32](rec_size_ptr[0])

  # Read record count (4 bytes)
  n = syscall3(SYS_read, STDIN, cast[int32](buffer + 8), 4)
  var rec_count_ptr: ptr int32 = cast[ptr int32](buffer + 8)
  var rec_count: int32 = rec_count_ptr[0]

  # Process records
  var match_count: int32 = 0
  var rec_buf_offset: int32 = 0
  var i: int32 = 0

  while i < rec_count:
    n = syscall3(SYS_read, STDIN, cast[int32](buffer + 12), rec_size)
    if n <= 0:
      break

    # Extract field value (int32 at field offset)
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

    if match != 0:
      # Copy record to output buffer
      var j: int32 = 0
      while j < rec_size:
        rec_buffer[rec_buf_offset + j] = buffer[12 + j]
        j = j + 1
      rec_buf_offset = rec_buf_offset + rec_size
      match_count = match_count + 1

    i = i + 1

  # Write schema header
  discard syscall3(SYS_write, STDOUT, cast[int32](buffer), 8)

  # Write filtered record count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(match_count)), 4)

  # Write matching records
  if match_count > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](rec_buffer), rec_buf_offset)

  discard syscall1(SYS_exit, 0)
