# link - Create hard link
# Usage: link target linkname

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_link: int32 = 9

const STDOUT: int32 = 1
const STDERR: int32 = 2

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
    print_err(cast[ptr uint8]("Usage: link target linkname\n"))
    discard syscall1(SYS_exit, 1)

  var target: ptr uint8 = get_argv(1)
  var linkname: ptr uint8 = get_argv(2)

  # Create hard link
  var result: int32 = syscall2(SYS_link, cast[int32](target), cast[int32](linkname))

  if result < 0:
    print_err(cast[ptr uint8]("link: cannot create link '"))
    print_err(linkname)
    print_err(cast[ptr uint8]("' to '"))
    print_err(target)
    print_err(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
