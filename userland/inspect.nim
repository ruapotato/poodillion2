# inspect - show schema and data from structured stream
# Part of PoodillionOS data tools

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print(msg: ptr uint8) =
  var i: int32 = 0
  while msg[i] != cast[uint8](0):
    i = i + 1
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), i)

proc println(msg: ptr uint8) =
  print(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

proc print_hex(val: uint8) =
  const hex: ptr uint8 = cast[ptr uint8]("0123456789abcdef")
  var buf: uint8 = 0
  var upper: uint8 = val >> 4
  var lower: uint8 = val & cast[uint8](15)

  discard syscall3(SYS_write, STDOUT, cast[int32](addr(hex[cast[int32](upper)])), 1)
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(hex[cast[int32](lower)])), 1)

proc main() =
  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read magic header
  var n: int32 = syscall3(SYS_read, STDIN, cast[int32](buffer), 4)
  if n != 4:
    println(cast[ptr uint8]("Error: No schema header"))
    discard syscall1(SYS_exit, 1)

  println(cast[ptr uint8]("=== Structured Data Stream ==="))
  print(cast[ptr uint8]("Magic: "))

  var i: int32 = 0
  while i < 4:
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(buffer[i])), 1)
    i = i + 1

  discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  # Read version
  n = syscall3(SYS_read, STDIN, cast[int32](buffer), 1)
  print(cast[ptr uint8]("Version: "))
  print_hex(buffer[0])
  println(cast[ptr uint8](""))

  # Read field count
  n = syscall3(SYS_read, STDIN, cast[int32](buffer), 1)
  print(cast[ptr uint8]("Fields: "))
  print_hex(buffer[0])
  println(cast[ptr uint8](""))

  # Read record size
  n = syscall3(SYS_read, STDIN, cast[int32](buffer), 2)
  print(cast[ptr uint8]("Record size: "))
  var rec_size: ptr uint16 = cast[ptr uint16](buffer)
  # TODO: print number

  println(cast[ptr uint8]("\n=== Binary Data ==="))

  # Read and display rest as hex dump
  var offset: int32 = 0
  var running: int32 = 1

  while running != 0:
    n = syscall3(SYS_read, STDIN, cast[int32](buffer), 16)
    if n <= 0:
      running = 0
    if n > 0:
      i = 0
      while i < n:
        print_hex(buffer[i])
        discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
        i = i + 1
      println(cast[ptr uint8](""))
      offset = offset + n

  discard syscall1(SYS_exit, 0)
