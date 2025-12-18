# shutdown - Shutdown system
# Usage:
#   shutdown -h  - halt system
#   shutdown -r  - reboot system
#   shutdown -p  - power off system

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_kill: int32 = 37
const SYS_sync: int32 = 36
const SYS_reboot: int32 = 88
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

# Signals
const SIGTERM: int32 = 15
const SIGKILL: int32 = 9

# Reboot commands
const LINUX_REBOOT_CMD_HALT: int32 = 0xCDEF0123
const LINUX_REBOOT_CMD_POWER_OFF: int32 = 0x4321FEDC
const LINUX_REBOOT_CMD_RESTART: int32 = 0x01234567

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc syscall4(num: int32, arg1: int32, arg2: int32, arg3: int32, arg4: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

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

# Sleep for a short time
proc sleep_brief() =
  var i: int32 = 0
  while i < 10000000:
    i = i + 1

proc usage() =
  print_err(cast[ptr uint8]("Usage: shutdown [OPTION]\n"))
  print_err(cast[ptr uint8]("\nOptions:\n"))
  print_err(cast[ptr uint8]("  -h    Halt the system\n"))
  print_err(cast[ptr uint8]("  -r    Reboot the system\n"))
  print_err(cast[ptr uint8]("  -p    Power off the system\n"))

# Perform shutdown sequence
proc do_shutdown(cmd: int32, action_msg: ptr uint8) =
  print(cast[ptr uint8]("shutdown: "))
  print(action_msg)
  print(cast[ptr uint8]("\n"))

  # Step 1: Send SIGTERM to all processes
  print(cast[ptr uint8]("shutdown: sending SIGTERM to all processes...\n"))
  discard syscall2(SYS_kill, 0 - 1, SIGTERM)

  # Step 2: Wait briefly for processes to terminate gracefully
  print(cast[ptr uint8]("shutdown: waiting for processes to terminate...\n"))
  sleep_brief()

  # Step 3: Send SIGKILL to remaining processes
  print(cast[ptr uint8]("shutdown: sending SIGKILL to remaining processes...\n"))
  discard syscall2(SYS_kill, 0 - 1, SIGKILL)

  # Step 4: Sync filesystems
  print(cast[ptr uint8]("shutdown: syncing filesystems...\n"))
  discard syscall1(SYS_sync, 0)
  discard syscall1(SYS_sync, 0)
  discard syscall1(SYS_sync, 0)

  # Step 5: Call reboot syscall
  print(cast[ptr uint8]("shutdown: executing system "))
  print(action_msg)
  print(cast[ptr uint8]("...\n"))

  # SYS_reboot: syscall4(88, MAGIC1, MAGIC2, cmd, 0)
  # MAGIC1 = 0xfee1dead, MAGIC2 = 672274793
  var magic1: int32 = 0 - 18751827  # 0xfee1dead as signed int32
  var magic2: int32 = 672274793     # 0x28121969
  var result: int32 = syscall4(SYS_reboot, magic1, magic2, cmd, 0)

  # If we get here, reboot failed
  print_err(cast[ptr uint8]("shutdown: failed to execute system command\n"))
  discard syscall1(SYS_exit, 1)

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    usage()
    discard syscall1(SYS_exit, 1)

  var arg: ptr uint8 = get_argv(1)

  # Check for -h, -r, -p flags
  if arg[0] == cast[uint8](45):  # '-'
    if arg[1] == cast[uint8](104):  # 'h'
      do_shutdown(LINUX_REBOOT_CMD_HALT, cast[ptr uint8]("halting system"))
    if arg[1] == cast[uint8](114):  # 'r'
      do_shutdown(LINUX_REBOOT_CMD_RESTART, cast[ptr uint8]("rebooting system"))
    if arg[1] == cast[uint8](112):  # 'p'
      do_shutdown(LINUX_REBOOT_CMD_POWER_OFF, cast[ptr uint8]("powering off system"))

  # Unknown option
  usage()
  discard syscall1(SYS_exit, 1)
