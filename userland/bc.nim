# bc - Simple calculator
# Supports: + - * / %
# Example: echo "2 + 3 * 4" | bc -> 14

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# Print integer
proc print_int(n: int32) =
  if n < 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("-"), 1)
    n = 0 - n

  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var i: int32 = 0
  var num: int32 = n
  while num > 0:
    buf[i] = cast[uint8](48 + (num % 10))
    num = num / 10
    i = i + 1

  var j: int32 = i - 1
  while j >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buf + j), 1)
    j = j - 1

proc main() =
  # Allocate buffers
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)

  var input: ptr uint8 = cast[ptr uint8](old_brk)
  var nums: ptr int32 = cast[ptr int32](old_brk + 4096)
  var ops: ptr uint8 = cast[ptr uint8](old_brk + 6144)

  # Read input
  var len: int32 = syscall3(SYS_read, STDIN, cast[int32](input), 4096)
  if len <= 0:
    discard syscall1(SYS_exit, 0)

  # Parse numbers and operators
  var pos: int32 = 0
  var num_count: int32 = 0
  var op_count: int32 = 0

  # Parse first number
  var num: int32 = 0
  while pos < len:
    var c: uint8 = input[pos]
    if c >= cast[uint8](48) and c <= cast[uint8](57):
      num = num * 10 + cast[int32](c) - 48
      pos = pos + 1
    else:
      break

  nums[num_count] = num
  num_count = num_count + 1

  # Parse rest of expression
  while pos < len:
    var c: uint8 = input[pos]

    # Skip whitespace
    if c == cast[uint8](32) or c == cast[uint8](9):
      pos = pos + 1
    else:
      # Check for newline or end
      if c == cast[uint8](10) or c == cast[uint8](13):
        break

      # Check for operator
      if c == cast[uint8](43) or c == cast[uint8](45) or c == cast[uint8](42) or c == cast[uint8](47) or c == cast[uint8](37):
        var op: uint8 = c
        pos = pos + 1

        # Skip whitespace
        while pos < len:
          c = input[pos]
          if c == cast[uint8](32) or c == cast[uint8](9):
            pos = pos + 1
          else:
            break

        # Parse next number
        num = 0
        while pos < len:
          c = input[pos]
          if c >= cast[uint8](48) and c <= cast[uint8](57):
            num = num * 10 + cast[int32](c) - 48
            pos = pos + 1
          else:
            break

        # Handle * / % immediately
        if op == cast[uint8](42):
          nums[num_count - 1] = nums[num_count - 1] * num
        else:
          if op == cast[uint8](47):
            if num != 0:
              nums[num_count - 1] = nums[num_count - 1] / num
          else:
            if op == cast[uint8](37):
              if num != 0:
                nums[num_count - 1] = nums[num_count - 1] % num
            else:
              # + or -, save
              ops[op_count] = op
              op_count = op_count + 1
              nums[num_count] = num
              num_count = num_count + 1
      else:
        break

  # Apply + and -
  var result: int32 = nums[0]
  var i: int32 = 0
  while i < op_count:
    if ops[i] == cast[uint8](43):
      result = result + nums[i + 1]
    else:
      result = result - nums[i + 1]
    i = i + 1

  print_int(result)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  discard syscall1(SYS_exit, 0)
