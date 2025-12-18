# groups - Print group memberships
# Usage: groups [USER]
# Uses SYS_getgroups (80) for current user
# Prints group IDs (numeric)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getgroups: int32 = 80

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

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

  # Allocate buffer for number
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
  var argc: int32 = get_argc()

  # For now, we only support current user (no argument)
  # Supporting arbitrary users would require parsing /etc/group
  if argc > 1:
    print_err(cast[ptr uint8]("groups: user lookup not yet supported\n"))
    discard syscall1(SYS_exit, 1)

  # Allocate buffer for group IDs
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 512  # Space for up to 128 group IDs (4 bytes each)
  discard syscall1(SYS_brk, new_brk)
  var gid_list: ptr int32 = cast[ptr int32](old_brk)

  # Get groups (first call to get count)
  var ngroups: int32 = syscall2(SYS_getgroups, 0, 0)
  if ngroups < 0:
    print_err(cast[ptr uint8]("groups: cannot get group list\n"))
    discard syscall1(SYS_exit, 1)

  # Get actual groups
  if ngroups > 0:
    var ret: int32 = syscall2(SYS_getgroups, ngroups, cast[int32](gid_list))
    if ret < 0:
      print_err(cast[ptr uint8]("groups: cannot get group list\n"))
      discard syscall1(SYS_exit, 1)
    ngroups = ret

  # Print groups
  if ngroups == 0:
    print(cast[ptr uint8]("0\n"))
  else:
    var i: int32 = 0
    while i < ngroups:
      if i > 0:
        print(cast[ptr uint8](" "))
      print_int(gid_list[i])
      i = i + 1
    print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
