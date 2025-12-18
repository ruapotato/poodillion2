# shutdown - Shutdown system
# Usage:
#   shutdown -h now  - halt system
#   shutdown -r now  - reboot system
#   shutdown -p now  - power off system
#
# Process:
# 1. Send SIGTERM to all processes
# 2. Wait briefly
# 3. Send SIGKILL to remaining processes
# 4. Sync filesystems
# 5. Call SYS_reboot with appropriate command

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_kill: int32 = 37
const SYS_sync: int32 = 36
const SYS_reboot: int32 = 88
const SYS_nanosleep: int32 = 162
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

# Signals
const SIGTERM: int32 = 15
const SIGKILL: int32 = 9

# Note: Mini-Nim doesn't support arithmetic in const expressions
# Using direct decimal values instead

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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

# Sleep for a short time (naive busy wait since nanosleep needs struct)
proc sleep_brief() =
  var i: int32 = 0
  while i < 10000000:
    i = i + 1

proc usage() =
  print_err(cast[ptr uint8]("Usage: shutdown [OPTION]\n"))
  print_err(cast[ptr uint8]("\n"))
  print_err(cast[ptr uint8]("Options:\n"))
  print_err(cast[ptr uint8]("  -h    Halt the system\n"))
  print_err(cast[ptr uint8]("  -r    Reboot the system\n"))
  print_err(cast[ptr uint8]("  -p    Power off the system\n"))
  print_err(cast[ptr uint8]("\n"))
  print_err(cast[ptr uint8]("Examples:\n"))
  print_err(cast[ptr uint8]("  shutdown -h    # Halt\n"))
  print_err(cast[ptr uint8]("  shutdown -r    # Reboot\n"))
  print_err(cast[ptr uint8]("  shutdown -p    # Power off\n"))

# Perform shutdown sequence
proc do_shutdown(cmd: int32, action_msg: ptr uint8) =
  print(cast[ptr uint8]("shutdown: "))
  print(action_msg)
  print(cast[ptr uint8]("\n"))

  # Step 1: Send SIGTERM to all processes
  print(cast[ptr uint8]("shutdown: sending SIGTERM to all processes...\n"))
  # kill(-1, SIGTERM) sends signal to all processes we have permission to kill
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
  discard syscall1(SYS_sync, 0)  # Sync twice for safety
  discard syscall1(SYS_sync, 0)

  # Step 5: Call reboot syscall
  print(cast[ptr uint8]("shutdown: executing system "))
  print(action_msg)
  print(cast[ptr uint8]("...\n"))

  # SYS_reboot: syscall4(88, MAGIC1, MAGIC2, cmd, 0)
  # MAGIC1 = 0xfee1dead = -18751827 (signed), MAGIC2 = 672274793
  var magic1: int32 = 4276215469  # 0xfee1dead unsigned
  var magic2: int32 = 672274793
  var result: int32 = syscall4(SYS_reboot, magic1, magic2, cmd, 0)

  # If we get here, reboot failed
  print_err(cast[ptr uint8]("shutdown: failed to execute system command\n"))
  print_err(cast[ptr uint8]("shutdown: you may need root privileges\n"))
  discard syscall1(SYS_exit, 1)

proc main() =
  # For demonstration, show usage
  # In a full implementation, this would parse argc/argv

  usage()

  print(cast[ptr uint8]("\n"))
  print(cast[ptr uint8]("Note: shutdown requires root privileges.\n"))
  print(cast[ptr uint8]("This is a demonstration utility showing the shutdown sequence.\n"))
  print(cast[ptr uint8]("\n"))

  # Example shutdown operations (commented out - DANGEROUS!)
  # Uncomment only if you want to actually shutdown/reboot!
  #
  # For halt:
  # do_shutdown(LINUX_REBOOT_CMD_HALT, cast[ptr uint8]("halt"))
  #
  # For reboot:
  # do_shutdown(LINUX_REBOOT_CMD_RESTART, cast[ptr uint8]("reboot"))
  #
  # For power off:
  # do_shutdown(LINUX_REBOOT_CMD_POWER_OFF, cast[ptr uint8]("power off"))

  discard syscall1(SYS_exit, 0)
