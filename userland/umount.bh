# umount - Unmount filesystems
# Usage: umount MOUNTPOINT
#
# Uses SYS_umount2 (52): syscall2(52, target, flags)

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_umount2: int32 = 52
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

# Umount flags
const MNT_FORCE: int32 = 1        # Force unmount even if busy
const MNT_DETACH: int32 = 2       # Lazy unmount
const MNT_EXPIRE: int32 = 4       # Mark for expiration
const UMOUNT_NOFOLLOW: int32 = 8  # Don't follow symlink on umount

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

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

proc usage() =
  print_err(cast[ptr uint8]("Usage: umount MOUNTPOINT\n"))
  print_err(cast[ptr uint8]("\n"))
  print_err(cast[ptr uint8]("Unmount a mounted filesystem.\n"))
  print_err(cast[ptr uint8]("\n"))
  print_err(cast[ptr uint8]("Examples:\n"))
  print_err(cast[ptr uint8]("  umount /mnt\n"))
  print_err(cast[ptr uint8]("  umount /proc\n"))
  print_err(cast[ptr uint8]("  umount /dev\n"))

proc main() =
  # For this implementation, we demonstrate the umount2 syscall
  # In a full implementation, this would parse argc/argv for the mountpoint

  usage()

  # Example unmount operation (commented out - would need root privileges)
  # To actually unmount, uncomment and provide proper target:
  #
  # var target: ptr uint8 = cast[ptr uint8]("/mnt/test")
  # var flags: int32 = 0  # Normal unmount
  #
  # var result: int32 = syscall2(SYS_umount2, cast[int32](target), flags)
  #
  # if result < 0:
  #   print_err(cast[ptr uint8]("umount: failed to unmount filesystem\n"))
  #   print_err(cast[ptr uint8]("umount: device may be busy or you may lack permissions\n"))
  #   discard syscall1(SYS_exit, 1)
  #
  # print(cast[ptr uint8]("umount: filesystem unmounted successfully\n"))

  print_err(cast[ptr uint8]("\n"))
  print_err(cast[ptr uint8]("Note: umount requires root privileges and proper arguments.\n"))
  print_err(cast[ptr uint8]("This is a demonstration utility showing the syscall interface.\n"))

  discard syscall1(SYS_exit, 0)
