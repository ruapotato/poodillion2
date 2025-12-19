# id - Print user and group IDs
# Uses getuid, getgid, geteuid, getegid syscalls

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getuid: int32 = 24
const SYS_getgid: int32 = 47
const SYS_geteuid: int32 = 49
const SYS_getegid: int32 = 50

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n

  # Count digits
  var temp: int32 = num
  var digits: int32 = 0
  while temp > 0:
    digits = digits + 1
    temp = temp / 10

  # Allocate buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var pos: int32 = digits
  buf[pos] = cast[uint8](0)
  pos = pos - 1

  temp = num
  while temp > 0:
    var digit: int32 = temp % 10
    buf[pos] = cast[uint8](48 + digit)
    pos = pos - 1
    temp = temp / 10

  print(buf)

proc main() =
  # Get all user/group IDs
  var uid: int32 = syscall1(SYS_getuid, 0)
  var gid: int32 = syscall1(SYS_getgid, 0)
  var euid: int32 = syscall1(SYS_geteuid, 0)
  var egid: int32 = syscall1(SYS_getegid, 0)

  # Print uid
  print(cast[ptr uint8]("uid="))
  print_int(uid)

  # Print gid
  print(cast[ptr uint8](" gid="))
  print_int(gid)

  # Print euid if different from uid
  if euid != uid:
    print(cast[ptr uint8](" euid="))
    print_int(euid)

  # Print egid if different from gid
  if egid != gid:
    print(cast[ptr uint8](" egid="))
    print_int(egid)

  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
