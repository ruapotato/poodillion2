# cp - copy file
# Usage: cp source destination

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

# File open flags
const O_RDONLY: int32 = 0
const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_TRUNC: int32 = 512

# File permissions: 0644 (rw-r--r--)
const S_IRUSR: int32 = 256   # 0400 - user r
const S_IWUSR: int32 = 128   # 0200 - user w
const S_IRGRP: int32 = 32    # 0040 - group r
const S_IROTH: int32 = 4     # 0004 - others r

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

proc main() =
  var argc: int32 = get_argc()

  if argc < 3:
    print_err(cast[ptr uint8]("Usage: cp source destination\n"))
    discard syscall1(SYS_exit, 1)

  var source: ptr uint8 = get_argv(1)
  var dest: ptr uint8 = get_argv(2)

  # Open source file for reading
  var src_fd: int32 = syscall3(SYS_open, cast[int32](source), O_RDONLY, 0)
  if src_fd < 0:
    print_err(cast[ptr uint8]("cp: cannot open source file\n"))
    discard syscall1(SYS_exit, 1)

  # Create destination file for writing
  var mode: int32 = S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH
  var dest_fd: int32 = syscall3(SYS_open, cast[int32](dest), O_WRONLY | O_CREAT | O_TRUNC, mode)
  if dest_fd < 0:
    print_err(cast[ptr uint8]("cp: cannot create destination file\n"))
    discard syscall1(SYS_close, src_fd)
    discard syscall1(SYS_exit, 1)

  # Allocate buffer for copying
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Copy loop: read from source, write to destination
  var running: int32 = 1
  while running != 0:
    var bytes_read: int32 = syscall3(SYS_read, src_fd, cast[int32](buffer), 4096)

    if bytes_read < 0:
      print_err(cast[ptr uint8]("cp: read error\n"))
      discard syscall1(SYS_close, src_fd)
      discard syscall1(SYS_close, dest_fd)
      discard syscall1(SYS_exit, 1)

    if bytes_read == 0:
      running = 0

    if bytes_read > 0:
      var bytes_written: int32 = syscall3(SYS_write, dest_fd, cast[int32](buffer), bytes_read)
      if bytes_written != bytes_read:
        print_err(cast[ptr uint8]("cp: write error\n"))
        discard syscall1(SYS_close, src_fd)
        discard syscall1(SYS_close, dest_fd)
        discard syscall1(SYS_exit, 1)

  # Close both files
  discard syscall1(SYS_close, src_fd)
  discard syscall1(SYS_close, dest_fd)
  discard syscall1(SYS_exit, 0)
