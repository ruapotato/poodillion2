# reboot - Reboot the system
# Usage: reboot
#
# Simple wrapper: sync filesystems + reboot syscall

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
  print(cast[ptr uint8]("reboot: syncing filesystems...\n"))

  # Sync filesystems three times for safety
  discard syscall1(SYS_sync, 0)
  discard syscall1(SYS_sync, 0)
  discard syscall1(SYS_sync, 0)

  print(cast[ptr uint8]("reboot: rebooting system now...\n"))

  # Call reboot syscall
  # SYS_reboot: syscall4(88, MAGIC1, MAGIC2, cmd, 0)
  # MAGIC1 = 0xfee1dead, MAGIC2 = 672274793, CMD_RESTART = 0x01234567 = 19088743
  var magic1: int32 = 4276215469
  var magic2: int32 = 672274793
  var cmd: int32 = 19088743
  var result: int32 = syscall4(SYS_reboot, magic1, magic2, cmd, 0)

  # If we get here, reboot failed
  print_err(cast[ptr uint8]("reboot: failed to reboot system\n"))
  print_err(cast[ptr uint8]("reboot: you may need root privileges\n"))
  discard syscall1(SYS_exit, 1)
