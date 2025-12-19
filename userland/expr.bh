# expr - Evaluate expressions
# Usage: expr ARG1 OP ARG2
# Supports arithmetic and comparison operations

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

# String length
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

# String compare
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0) and s2[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      if s1[i] < s2[i]:
        return -1
      else:
        return 1
    i = i + 1
  if s1[i] == cast[uint8](0) and s2[i] == cast[uint8](0):
    return 0
  if s1[i] == cast[uint8](0):
    return -1
  return 1

# String to integer
proc atoi(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  var negative: int32 = 0

  while s[i] == cast[uint8](32) or s[i] == cast[uint8](9):
    i = i + 1

  if s[i] == cast[uint8](45):  # '-'
    negative = 1
    i = i + 1
  if s[i] == cast[uint8](43):  # '+'
    i = i + 1

  while s[i] >= cast[uint8](48) and s[i] <= cast[uint8](57):
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1

  if negative != 0:
    result = 0 - result
  return result

# Integer to string (using allocated buffer)
proc itoa(value: int32, buf: ptr uint8): int32 =
  var i: int32 = 0
  var n: int32 = value
  var is_negative: int32 = 0

  if n < 0:
    is_negative = 1
    n = 0 - n

  # Handle 0 specially
  if n == 0:
    buf[0] = cast[uint8](48)  # '0'
    buf[1] = cast[uint8](0)
    return 1

  # Convert to string (backwards)
  var tmp: ptr uint8 = cast[ptr uint8](cast[int32](buf) + 64)  # temp buffer
  var j: int32 = 0

  while n > 0:
    tmp[j] = cast[uint8](48 + (n % 10))
    n = n / 10
    j = j + 1

  # Add minus sign if negative
  if is_negative != 0:
    buf[i] = cast[uint8](45)  # '-'
    i = i + 1

  # Copy reversed
  j = j - 1
  while j >= 0:
    buf[i] = tmp[j]
    i = i + 1
    j = j - 1

  buf[i] = cast[uint8](0)
  return i

# Print string
proc print(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

# Print error
proc print_err(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDERR, cast[int32](s), len)

proc main() =
  var argc: int32 = get_argc()

  if argc != 4:
    print_err(cast[ptr uint8]("Usage: expr ARG1 OP ARG2\n"))
    discard syscall1(SYS_exit, 1)

  # Allocate buffer for output
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 256
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var arg1: ptr uint8 = get_argv(1)
  var op: ptr uint8 = get_argv(2)
  var arg2: ptr uint8 = get_argv(3)

  # Parse integers
  var val1: int32 = atoi(arg1)
  var val2: int32 = atoi(arg2)
  var result: int32 = 0

  # Arithmetic operations
  if strcmp(op, cast[ptr uint8]("+")) == 0:
    result = val1 + val2
    var len: int32 = itoa(result, buf)
    discard syscall3(SYS_write, STDOUT, cast[int32](buf), len)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("-")) == 0:
    result = val1 - val2
    var len: int32 = itoa(result, buf)
    discard syscall3(SYS_write, STDOUT, cast[int32](buf), len)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("*")) == 0:
    result = val1 * val2
    var len: int32 = itoa(result, buf)
    discard syscall3(SYS_write, STDOUT, cast[int32](buf), len)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("/")) == 0:
    if val2 == 0:
      print_err(cast[ptr uint8]("expr: division by zero\n"))
      discard syscall1(SYS_exit, 1)
    result = val1 / val2
    var len: int32 = itoa(result, buf)
    discard syscall3(SYS_write, STDOUT, cast[int32](buf), len)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("%")) == 0:
    if val2 == 0:
      print_err(cast[ptr uint8]("expr: division by zero\n"))
      discard syscall1(SYS_exit, 1)
    result = val1 % val2
    var len: int32 = itoa(result, buf)
    discard syscall3(SYS_write, STDOUT, cast[int32](buf), len)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    discard syscall1(SYS_exit, 0)

  # Comparison operations (return 1 for true, 0 for false)
  if strcmp(op, cast[ptr uint8]("=")) == 0:
    if strcmp(arg1, arg2) == 0:
      print(cast[ptr uint8]("1\n"))
    else:
      print(cast[ptr uint8]("0\n"))
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("!=")) == 0:
    if strcmp(arg1, arg2) != 0:
      print(cast[ptr uint8]("1\n"))
    else:
      print(cast[ptr uint8]("0\n"))
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("<")) == 0:
    if val1 < val2:
      print(cast[ptr uint8]("1\n"))
    else:
      print(cast[ptr uint8]("0\n"))
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8]("<=")) == 0:
    if val1 <= val2:
      print(cast[ptr uint8]("1\n"))
    else:
      print(cast[ptr uint8]("0\n"))
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8](">")) == 0:
    if val1 > val2:
      print(cast[ptr uint8]("1\n"))
    else:
      print(cast[ptr uint8]("0\n"))
    discard syscall1(SYS_exit, 0)

  if strcmp(op, cast[ptr uint8](">=")) == 0:
    if val1 >= val2:
      print(cast[ptr uint8]("1\n"))
    else:
      print(cast[ptr uint8]("0\n"))
    discard syscall1(SYS_exit, 0)

  print_err(cast[ptr uint8]("expr: unknown operator\n"))
  discard syscall1(SYS_exit, 1)
