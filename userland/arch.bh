# arch - Print machine architecture
# Usage: arch
# Uses SYS_uname (122) to get machine field from utsname

const SYS_uname: int32 = 122
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

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

proc main() =
  # Allocate memory for utsname struct
  # struct utsname has 5 fields of 65 bytes each = 325 bytes
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 512
  discard syscall1(SYS_brk, new_brk)

  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  # Call uname syscall
  var result: int32 = syscall1(SYS_uname, cast[int32](buf))

  if result < 0:
    print(cast[ptr uint8]("arch: failed to get system information\n"))
    discard syscall1(SYS_exit, 1)

  # utsname struct layout (each field is 65 bytes):
  # char sysname[65];    - OS name (e.g., "Linux")
  # char nodename[65];   - hostname
  # char release[65];    - kernel release
  # char version[65];    - kernel version
  # char machine[65];    - hardware architecture

  # machine field is at offset 260 (4 * 65)
  var machine: ptr uint8 = cast[ptr uint8](cast[int32](buf) + 260)

  # Print machine architecture
  print(machine)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
