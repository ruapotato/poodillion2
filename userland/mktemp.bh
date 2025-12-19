# mktemp - Create temporary file or directory
# Usage: mktemp [-d] [TEMPLATE]
# Default template: /tmp/tmp.XXXXXX
# -d creates directory instead of file

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_mkdir: int32 = 39
const SYS_time: int32 = 13

const STDOUT: int32 = 1
const STDERR: int32 = 2

# File flags
const O_RDWR: int32 = 2
const O_CREAT: int32 = 64
const O_EXCL: int32 = 128

# Permissions: 0600 for files, 0700 for dirs
const S_IRUSR: int32 = 256   # 0400 - user r
const S_IWUSR: int32 = 128   # 0200 - user w
const S_IXUSR: int32 = 64    # 0100 - user x

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

# Copy string
proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

# Compare strings
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return 1
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 1
  return 0

# Simple pseudo-random number generator
var rand_seed: int32 = 0

proc srand(seed: int32) =
  rand_seed = seed

proc rand(): int32 =
  rand_seed = (rand_seed * 1103515245 + 12345)
  return (rand_seed >> 16) & 32767

# Convert int to char (0-9, a-z)
proc int_to_char(n: int32): uint8 =
  var val: int32 = n % 36
  if val < 10:
    return cast[uint8](48 + val)
  return cast[uint8](97 + val - 10)

# Replace X characters in template with random chars
proc fill_template(template: ptr uint8, output: ptr uint8): int32 =
  var i: int32 = 0
  var x_count: int32 = 0

  # Copy template and count X's
  while template[i] != cast[uint8](0):
    output[i] = template[i]
    if template[i] == cast[uint8](88):  # 'X'
      x_count = x_count + 1
    i = i + 1
  output[i] = cast[uint8](0)

  if x_count == 0:
    return 0

  # Replace X's from right to left with random chars
  var j: int32 = i - 1
  while j >= 0:
    if output[j] == cast[uint8](88):
      var r: int32 = rand()
      output[j] = int_to_char(r)
    j = j - 1

  return 1

proc main() =
  var argc: int32 = get_argc()
  var make_dir: int32 = 0
  var template: ptr uint8 = cast[ptr uint8](0)

  # Parse arguments
  var arg_idx: int32 = 1
  if argc >= 2:
    var arg1: ptr uint8 = get_argv(1)
    var is_d: int32 = strcmp(arg1, cast[ptr uint8]("-d"))
    if is_d == 0:
      make_dir = 1
      arg_idx = 2

  if argc > arg_idx:
    template = get_argv(arg_idx)
  else:
    template = cast[ptr uint8]("/tmp/tmp.XXXXXX")

  # Allocate buffer for path
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 512
  discard syscall1(SYS_brk, new_brk)
  var path: ptr uint8 = cast[ptr uint8](old_brk)

  # Initialize random seed with time
  var time_val: int32 = syscall1(SYS_time, 0)
  srand(time_val)

  # Try to create file/directory with random name
  var attempts: int32 = 0
  var max_attempts: int32 = 100
  var success: int32 = 0

  while attempts < max_attempts:
    var filled: int32 = fill_template(template, path)
    if filled == 0:
      print_err(cast[ptr uint8]("mktemp: template must contain XXXXXX\n"))
      discard syscall1(SYS_exit, 1)

    if make_dir != 0:
      # Try to create directory
      var mode: int32 = S_IRUSR | S_IWUSR | S_IXUSR
      var ret: int32 = syscall2(SYS_mkdir, cast[int32](path), mode)
      if ret == 0:
        success = 1
        break
    else:
      # Try to create file
      var mode: int32 = S_IRUSR | S_IWUSR
      var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDWR | O_CREAT | O_EXCL, mode)
      if fd >= 0:
        discard syscall1(SYS_close, fd)
        success = 1
        break

    attempts = attempts + 1

  if success == 0:
    print_err(cast[ptr uint8]("mktemp: failed to create temporary file/directory\n"))
    discard syscall1(SYS_exit, 1)

  # Print created path
  print(path)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
