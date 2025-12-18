# which - Locate command in PATH
# Usage: which COMMAND
# Searches ./bin/, /bin/, /usr/bin/

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_access: int32 = 33
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

const X_OK: int32 = 1  # executable

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

# String length
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

# String copy
proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

# String concatenate
proc strcat(dest: ptr uint8, src: ptr uint8) =
  var dest_len: int32 = strlen(dest)
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[dest_len + i] = src[i]
    i = i + 1
  dest[dest_len + i] = cast[uint8](0)

# Print string
proc print(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

# Print error
proc print_err(s: ptr uint8) =
  var len: int32 = strlen(s)
  discard syscall3(SYS_write, STDERR, cast[int32](s), len)

# Check if file is executable
proc is_executable(path: ptr uint8): int32 =
  var ret: int32 = syscall2(SYS_access, cast[int32](path), X_OK)
  if ret >= 0:
    return 1
  return 0

# Search for command in a directory
proc search_in_dir(dir: ptr uint8, cmd: ptr uint8, path_buf: ptr uint8): int32 =
  # Build path: dir/cmd
  strcpy(path_buf, dir)
  strcat(path_buf, cast[ptr uint8]("/"))
  strcat(path_buf, cmd)

  if is_executable(path_buf) != 0:
    return 1
  return 0

proc main() =
  var argc: int32 = get_argc()

  if argc != 2:
    print_err(cast[ptr uint8]("Usage: which COMMAND\n"))
    discard syscall1(SYS_exit, 1)

  var cmd: ptr uint8 = get_argv(1)

  # Allocate buffer for path construction
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 512
  discard syscall1(SYS_brk, new_brk)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk)

  # Search in ./bin/
  if search_in_dir(cast[ptr uint8]("./bin"), cmd, path_buf) != 0:
    print(path_buf)
    print(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 0)

  # Search in /bin/
  if search_in_dir(cast[ptr uint8]("/bin"), cmd, path_buf) != 0:
    print(path_buf)
    print(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 0)

  # Search in /usr/bin/
  if search_in_dir(cast[ptr uint8]("/usr/bin"), cmd, path_buf) != 0:
    print(path_buf)
    print(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 0)

  # Not found
  discard syscall1(SYS_exit, 1)
