# ln - Create links between files
# Usage: ln target linkname (hard link)
#        ln -s target linkname (symbolic link)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_link: int32 = 9
const SYS_symlink: int32 = 83

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

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

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while true:
    if s1[i] != s2[i]:
      return 1
    if s1[i] == cast[uint8](0):
      return 0
    i = i + 1
  return 0

proc main() =
  var argc: int32 = get_argc()

  # Parse arguments
  var symbolic: int32 = 0
  var target: ptr uint8 = cast[ptr uint8](0)
  var linkname: ptr uint8 = cast[ptr uint8](0)
  var arg_idx: int32 = 1

  # Check for -s flag
  if argc > 1:
    var arg1: ptr uint8 = get_argv(1)
    if arg1[0] == cast[uint8](45) and arg1[1] == cast[uint8](115):  # "-s"
      symbolic = 1
      arg_idx = 2

  # Get target and linkname
  if arg_idx < argc:
    target = get_argv(arg_idx)
    arg_idx = arg_idx + 1

  if arg_idx < argc:
    linkname = get_argv(arg_idx)

  # Validate arguments
  if target == cast[ptr uint8](0) or linkname == cast[ptr uint8](0):
    print_err(cast[ptr uint8]("Usage: ln [-s] target linkname\n"))
    print_err(cast[ptr uint8]("  -s  create symbolic link instead of hard link\n"))
    discard syscall1(SYS_exit, 1)

  # Create link
  var ret: int32 = 0
  if symbolic != 0:
    # Create symbolic link
    ret = syscall2(SYS_symlink, cast[int32](target), cast[int32](linkname))
    if ret < 0:
      print_err(cast[ptr uint8]("ln: failed to create symbolic link '"))
      print_err(linkname)
      print_err(cast[ptr uint8]("' -> '"))
      print_err(target)
      print_err(cast[ptr uint8]("'\n"))
      discard syscall1(SYS_exit, 1)
  else:
    # Create hard link
    ret = syscall2(SYS_link, cast[int32](target), cast[int32](linkname))
    if ret < 0:
      print_err(cast[ptr uint8]("ln: failed to create hard link '"))
      print_err(linkname)
      print_err(cast[ptr uint8]("' -> '"))
      print_err(target)
      print_err(cast[ptr uint8]("'\n"))
      discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
