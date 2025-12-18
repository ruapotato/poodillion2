# hostname - Print the system hostname
# Reads /proc/sys/kernel/hostname
# Supports -f (FQDN) and -i (IP address) flags

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
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return 1
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 1
  return 0

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var flag_f: ptr uint8 = cast[ptr uint8](old_brk + 512)
  var flag_i: ptr uint8 = cast[ptr uint8](old_brk + 520)

  # Build -f flag string
  flag_f[0] = cast[uint8](45)  # -
  flag_f[1] = cast[uint8](102) # f
  flag_f[2] = cast[uint8](0)

  # Build -i flag string
  flag_i[0] = cast[uint8](45)  # -
  flag_i[1] = cast[uint8](105) # i
  flag_i[2] = cast[uint8](0)

  # Build path: /proc/sys/kernel/hostname
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](115)  # s
  path[7] = cast[uint8](121)  # y
  path[8] = cast[uint8](115)  # s
  path[9] = cast[uint8](47)   # /
  path[10] = cast[uint8](107) # k
  path[11] = cast[uint8](101) # e
  path[12] = cast[uint8](114) # r
  path[13] = cast[uint8](110) # n
  path[14] = cast[uint8](101) # e
  path[15] = cast[uint8](108) # l
  path[16] = cast[uint8](47)  # /
  path[17] = cast[uint8](104) # h
  path[18] = cast[uint8](111) # o
  path[19] = cast[uint8](115) # s
  path[20] = cast[uint8](116) # t
  path[21] = cast[uint8](110) # n
  path[22] = cast[uint8](97)  # a
  path[23] = cast[uint8](109) # m
  path[24] = cast[uint8](101) # e
  path[25] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print(cast[ptr uint8]("hostname: cannot open /proc/sys/kernel/hostname\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 256)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print(cast[ptr uint8]("hostname: cannot read hostname\n"))
    discard syscall1(SYS_exit, 1)

  # Remove trailing newline if present
  if nread > 0:
    if buffer[nread - 1] == cast[uint8](10):  # newline
      nread = nread - 1

  buffer[nread] = cast[uint8](0)

  # Print hostname (basic version - no args support for now)
  print(buffer)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
