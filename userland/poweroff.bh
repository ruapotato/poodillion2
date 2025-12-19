# poweroff - Power off the system
# Usage: poweroff
#
# Simple wrapper: sync filesystems + power off syscall

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_sync: int32 = 36
const SYS_reboot: int32 = 88

const STDOUT: int32 = 1
const STDERR: int32 = 2

# Note: Using literals directly in syscall to avoid const arithmetic issues

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc syscall4(num: int32, arg1: int32, arg2: int32, arg3: int32, arg4: int32): int32

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

proc main() =
  print(cast[ptr uint8]("poweroff: syncing filesystems...\n"))

  # Sync filesystems three times for safety
  discard syscall1(SYS_sync, 0)
  discard syscall1(SYS_sync, 0)
  discard syscall1(SYS_sync, 0)

  print(cast[ptr uint8]("poweroff: powering off system now...\n"))

  # Call reboot syscall with POWER_OFF command
  # SYS_reboot: syscall4(88, MAGIC1, MAGIC2, cmd, 0)
  # MAGIC1 = 0xfee1dead, MAGIC2 = 672274793, CMD_POWER_OFF = 0x4321fedc = 1126162140
  var magic1: int32 = 4276215469
  var magic2: int32 = 672274793
  var cmd: int32 = 1126162140
  var result: int32 = syscall4(SYS_reboot, magic1, magic2, cmd, 0)

  # If we get here, poweroff failed
  print_err(cast[ptr uint8]("poweroff: failed to power off system\n"))
  print_err(cast[ptr uint8]("poweroff: you may need root privileges\n"))
  discard syscall1(SYS_exit, 1)
