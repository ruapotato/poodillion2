# cat - concatenate files and print on stdout
# Usage: cat [file...]
# If no files specified, read from stdin

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

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc cat_fd(fd: int32, buffer: ptr uint8) =
  var n: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
  while n > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer), n)
    n = syscall3(SYS_read, fd, cast[int32](buffer), 4096)

proc main() =
  var argc: int32 = get_argc()

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  if argc < 2:
    # No files - read from stdin
    cat_fd(STDIN, buffer)
  else:
    # Read each file
    var i: int32 = 1
    while i < argc:
      var filename: ptr uint8 = get_argv(i)

      # Check for "-" meaning stdin
      if filename[0] == cast[uint8](45):  # '-'
        if filename[1] == cast[uint8](0):
          cat_fd(STDIN, buffer)
          i = i + 1
          discard 0  # Skip to next iteration
        else:
          # It's a flag or filename starting with -
          i = i + 1
          discard 0
      else:
        # Open and read file
        var fd: int32 = syscall2(SYS_open, cast[int32](filename), O_RDONLY)
        if fd < 0:
          print_err(cast[ptr uint8]("cat: "))
          print_err(filename)
          print_err(cast[ptr uint8](": No such file or directory\n"))
        else:
          cat_fd(fd, buffer)
          discard syscall1(SYS_close, fd)
        i = i + 1

  discard syscall1(SYS_exit, 0)
