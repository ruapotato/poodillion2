# cmp - compare two files byte by byte
# Part of PoodillionOS text utilities
# Exit codes: 0 if identical, 1 if different, 2 if error

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
extern proc get_argv(index: int32): ptr uint8

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

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  var num: int32 = n
  var i: int32 = 0

  while num > 0:
    var digit: int32 = num % 10
    buffer[i] = cast[uint8](48 + digit)
    num = num / 10
    i = i + 1

  var j: int32 = i - 1
  while j >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer + j), 1)
    j = j - 1

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: cmp FILE1 FILE2\n"))
    discard syscall1(SYS_exit, 2)

  var file1: ptr uint8 = get_argv(1)
  var file2: ptr uint8 = get_argv(2)

  # Open both files
  var fd1: int32 = syscall3(SYS_open, cast[int32](file1), O_RDONLY, 0)
  if fd1 < 0:
    print_err(cast[ptr uint8]("cmp: cannot open "))
    print_err(file1)
    print_err(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 2)

  var fd2: int32 = syscall3(SYS_open, cast[int32](file2), O_RDONLY, 0)
  if fd2 < 0:
    print_err(cast[ptr uint8]("cmp: cannot open "))
    print_err(file2)
    print_err(cast[ptr uint8]("\n"))
    discard syscall1(SYS_close, fd1)
    discard syscall1(SYS_exit, 2)

  # Allocate two buffers
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buf1: ptr uint8 = cast[ptr uint8](old_brk)
  var buf2: ptr uint8 = cast[ptr uint8](old_brk + 4096)

  var byte_pos: int32 = 1  # 1-indexed byte position
  var line_num: int32 = 1  # 1-indexed line number
  var running: int32 = 1

  while running != 0:
    var n1: int32 = syscall3(SYS_read, fd1, cast[int32](buf1), 4096)
    var n2: int32 = syscall3(SYS_read, fd2, cast[int32](buf2), 4096)

    # Check for read errors
    if n1 < 0:
      print_err(cast[ptr uint8]("cmp: read error on "))
      print_err(file1)
      print_err(cast[ptr uint8]("\n"))
      discard syscall1(SYS_close, fd1)
      discard syscall1(SYS_close, fd2)
      discard syscall1(SYS_exit, 2)

    if n2 < 0:
      print_err(cast[ptr uint8]("cmp: read error on "))
      print_err(file2)
      print_err(cast[ptr uint8]("\n"))
      discard syscall1(SYS_close, fd1)
      discard syscall1(SYS_close, fd2)
      discard syscall1(SYS_exit, 2)

    # Check for EOF conditions
    # If one file ended but not the other, files differ in length
    if n1 == 0:
      if n2 > 0:
        print(file1)
        print(cast[ptr uint8](" "))
        print(file2)
        print(cast[ptr uint8](" differ: EOF on "))
        print(file1)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_close, fd1)
        discard syscall1(SYS_close, fd2)
        discard syscall1(SYS_exit, 1)

    if n2 == 0:
      if n1 > 0:
        print(file1)
        print(cast[ptr uint8](" "))
        print(file2)
        print(cast[ptr uint8](" differ: EOF on "))
        print(file2)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_close, fd1)
        discard syscall1(SYS_close, fd2)
        discard syscall1(SYS_exit, 1)

    # Both files ended - they are identical
    if n1 == 0:
      if n2 == 0:
        discard syscall1(SYS_close, fd1)
        discard syscall1(SYS_close, fd2)
        discard syscall1(SYS_exit, 0)

    # Compare bytes in this chunk
    var min_n: int32 = n1
    if n2 < n1:
      min_n = n2

    var i: int32 = 0
    while i < min_n:
      if buf1[i] != buf2[i]:
        # Found difference
        print(file1)
        print(cast[ptr uint8](" "))
        print(file2)
        print(cast[ptr uint8](" differ: byte "))
        print_int(byte_pos)
        print(cast[ptr uint8](", line "))
        print_int(line_num)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_close, fd1)
        discard syscall1(SYS_close, fd2)
        discard syscall1(SYS_exit, 1)

      # Count line numbers
      if buf1[i] == cast[uint8](10):
        line_num = line_num + 1

      byte_pos = byte_pos + 1
      i = i + 1

    # After comparing common bytes, check if chunk sizes differ
    if n1 != n2:
      # Files differ in length within same chunk
      if n1 < n2:
        print(file1)
        print(cast[ptr uint8](" "))
        print(file2)
        print(cast[ptr uint8](" differ: EOF on "))
        print(file1)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_close, fd1)
        discard syscall1(SYS_close, fd2)
        discard syscall1(SYS_exit, 1)
      if n1 > n2:
        print(file1)
        print(cast[ptr uint8](" "))
        print(file2)
        print(cast[ptr uint8](" differ: EOF on "))
        print(file2)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_close, fd1)
        discard syscall1(SYS_close, fd2)
        discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_close, fd1)
  discard syscall1(SYS_close, fd2)
  discard syscall1(SYS_exit, 0)
