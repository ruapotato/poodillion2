# install - Copy files with attributes
# Usage: install SRC DEST
#        install -m MODE SRC DEST

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_chmod: int32 = 15

const STDOUT: int32 = 1
const STDERR: int32 = 2

# File open flags
const O_RDONLY: int32 = 0
const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_TRUNC: int32 = 512

# Default mode: 0755 (rwxr-xr-x) - executable by default
const S_IRWXU: int32 = 448   # 0700 - user rwx
const S_IRGRP: int32 = 32    # 0040 - group r
const S_IXGRP: int32 = 8     # 0010 - group x
const S_IROTH: int32 = 4     # 0004 - others r
const S_IXOTH: int32 = 1     # 0001 - others x

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

# Compare strings
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return cast[int32](s1[i]) - cast[int32](s2[i])
    i = i + 1
  if s2[i] != cast[uint8](0):
    return -1
  return 0

# Check if character is octal digit (0-7)
proc is_octal_digit(c: uint8): int32 =
  if c >= cast[uint8](48):
    if c <= cast[uint8](55):
      return 1
  return 0

# Parse octal mode string to integer
proc parse_octal_mode(mode_str: ptr uint8): int32 =
  var mode: int32 = 0
  var i: int32 = 0

  while mode_str[i] != cast[uint8](0):
    var is_oct: int32 = is_octal_digit(mode_str[i])
    if is_oct == 0:
      return -1

    var digit: int32 = cast[int32](mode_str[i]) - 48
    mode = (mode << 3) | digit
    i = i + 1

  return mode

proc main() =
  var argc: int32 = get_argc()

  var source: ptr uint8
  var dest: ptr uint8
  var mode: int32 = S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH  # 0755

  # Parse arguments
  if argc == 3:
    # install SRC DEST (default mode)
    source = get_argv(1)
    dest = get_argv(2)
  else:
    if argc == 5:
      # install -m MODE SRC DEST
      var arg1: ptr uint8 = get_argv(1)
      var cmp_m: int32 = strcmp(arg1, cast[ptr uint8]("-m"))

      if cmp_m == 0:
        var mode_str: ptr uint8 = get_argv(2)
        mode = parse_octal_mode(mode_str)

        if mode < 0:
          print_err(cast[ptr uint8]("install: invalid mode\n"))
          discard syscall1(SYS_exit, 1)

        source = get_argv(3)
        dest = get_argv(4)
      else:
        print_err(cast[ptr uint8]("Usage: install [-m MODE] SRC DEST\n"))
        discard syscall1(SYS_exit, 1)
    else:
      print_err(cast[ptr uint8]("Usage: install [-m MODE] SRC DEST\n"))
      discard syscall1(SYS_exit, 1)

  # Open source file for reading
  var src_fd: int32 = syscall3(SYS_open, cast[int32](source), O_RDONLY, 0)
  if src_fd < 0:
    print_err(cast[ptr uint8]("install: cannot open source file\n"))
    discard syscall1(SYS_exit, 1)

  # Create destination file for writing
  var dest_fd: int32 = syscall3(SYS_open, cast[int32](dest), O_WRONLY | O_CREAT | O_TRUNC, mode)
  if dest_fd < 0:
    print_err(cast[ptr uint8]("install: cannot create destination file\n"))
    discard syscall1(SYS_close, src_fd)
    discard syscall1(SYS_exit, 1)

  # Allocate buffer for copying
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Copy loop
  var running: int32 = 1
  while running != 0:
    var bytes_read: int32 = syscall3(SYS_read, src_fd, cast[int32](buffer), 4096)

    if bytes_read < 0:
      print_err(cast[ptr uint8]("install: read error\n"))
      discard syscall1(SYS_close, src_fd)
      discard syscall1(SYS_close, dest_fd)
      discard syscall1(SYS_exit, 1)

    if bytes_read == 0:
      running = 0

    if bytes_read > 0:
      var bytes_written: int32 = syscall3(SYS_write, dest_fd, cast[int32](buffer), bytes_read)
      if bytes_written != bytes_read:
        print_err(cast[ptr uint8]("install: write error\n"))
        discard syscall1(SYS_close, src_fd)
        discard syscall1(SYS_close, dest_fd)
        discard syscall1(SYS_exit, 1)

  # Close both files
  discard syscall1(SYS_close, src_fd)
  discard syscall1(SYS_close, dest_fd)

  # Set permissions (in case umask affected them)
  discard syscall2(SYS_chmod, cast[int32](dest), mode)

  discard syscall1(SYS_exit, 0)
