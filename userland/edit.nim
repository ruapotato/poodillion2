# edit - PoodillionOS Text Editor
# A simple, fast CLI text editor
# Controls: Type to insert, Backspace to delete, Ctrl+S to save, Ctrl+Q to quit

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1

const O_RDONLY: int32 = 0
const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_TRUNC: int32 = 512

const S_IRUSR: int32 = 256
const S_IWUSR: int32 = 128
const S_IRGRP: int32 = 32
const S_IROTH: int32 = 4

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc write_str(s: ptr uint8, len: int32) =
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

proc write_char(c: uint8) =
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(c)), 1)

# ANSI escape codes
proc clear_screen() =
  write_str(cast[ptr uint8]("[2J[H"), 7)

proc invert_colors() =
  write_str(cast[ptr uint8]("[7m"), 4)

proc reset_colors() =
  write_str(cast[ptr uint8]("[0m"), 4)

proc newline() =
  write_char(cast[uint8](10))

# File operations
proc load_file(buffer: ptr uint8, capacity: int32): int32 =
  var fd: int32 = syscall3(SYS_open, cast[int32]("file.txt"), O_RDONLY, 0)
  if fd < 0:
    return 0
  var bytes_read: int32 = syscall3(SYS_read, fd, cast[int32](buffer), capacity)
  discard syscall1(SYS_close, fd)
  if bytes_read < 0:
    return 0
  return bytes_read

proc save_file(buffer: ptr uint8, size: int32) =
  var mode: int32 = S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH
  var fd: int32 = syscall3(SYS_open, cast[int32]("file.txt"), O_WRONLY | O_CREAT | O_TRUNC, mode)
  if fd >= 0:
    discard syscall3(SYS_write, fd, cast[int32](buffer), size)
    discard syscall1(SYS_close, fd)

# Display buffer
proc show_buffer(buffer: ptr uint8, size: int32) =
  clear_screen()
  write_str(cast[ptr uint8]("[ PoodillionOS Editor - file.txt ]"), 35)
  newline()
  newline()

  var i: int32 = 0
  while i < size:
    write_char(buffer[i])
    i = i + 1

  newline()
  newline()
  invert_colors()
  write_str(cast[ptr uint8](" Ctrl+S: Save | Ctrl+Q: Quit | Backspace: Delete "), 50)
  reset_colors()
  newline()

proc main() =
  # Allocate 16KB buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Load existing file
  var size: int32 = load_file(buffer, 16384)

  # Show initial state
  show_buffer(buffer, size)

  # Main edit loop
  var running: int32 = 1
  var input_byte: uint8 = 0

  while running != 0:
    var n: int32 = syscall3(SYS_read, STDIN, cast[int32](addr(input_byte)), 1)
    if n > 0:
      # Ctrl+Q = 17 (quit)
      if input_byte == cast[uint8](17):
        running = 0

      # Ctrl+S = 19 (save)
      if input_byte == cast[uint8](19):
        save_file(buffer, size)
        show_buffer(buffer, size)

      # Backspace = 127
      if input_byte == cast[uint8](127):
        if size > 0:
          size = size - 1
          show_buffer(buffer, size)

      # Backspace = 8
      if input_byte == cast[uint8](8):
        if size > 0:
          size = size - 1
          show_buffer(buffer, size)

      # Printable characters and newline
      if input_byte >= cast[uint8](32):
        if size < 16383:
          buffer[size] = input_byte
          size = size + 1
          show_buffer(buffer, size)

      if input_byte == cast[uint8](10):
        if size < 16383:
          buffer[size] = input_byte
          size = size + 1
          show_buffer(buffer, size)

  # Clean exit
  clear_screen()
  write_str(cast[ptr uint8]("Editor closed. File saved to file.txt"), 38)
  newline()
  discard syscall1(SYS_exit, 0)
