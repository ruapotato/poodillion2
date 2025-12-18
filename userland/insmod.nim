# insmod - Insert a kernel module
# Uses SYS_init_module (128) to load a kernel module
# Requires root privileges
# Part of PoodillionOS kernel utilities

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_init_module: int32 = 128
const SYS_fstat: int32 = 108

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2
const O_RDONLY: int32 = 0

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

proc print_error(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 2097152  # 2MB for module data
  discard syscall1(SYS_brk, new_brk)

  var module_path: ptr uint8 = cast[ptr uint8](old_brk)
  var module_data: ptr uint8 = cast[ptr uint8](old_brk + 4096)
  var stat_buf: ptr uint8 = cast[ptr uint8](old_brk + 2097152 - 4096)

  # Hardcoded test path - in full version would parse argv
  # Example: /lib/modules/$(uname -r)/kernel/fs/ext4/ext4.ko
  var test_path: ptr uint8 = cast[ptr uint8]("test.ko")

  # Build module path
  var i: int32 = 0
  while test_path[i] != cast[uint8](0):
    module_path[i] = test_path[i]
    i = i + 1
  module_path[i] = cast[uint8](0)

  # Open module file
  var fd: int32 = syscall3(SYS_open, cast[int32](module_path), O_RDONLY, 0)
  if fd < 0:
    print_error(cast[ptr uint8]("insmod: cannot open '"))
    print_error(module_path)
    print_error(cast[ptr uint8]("'\n"))
    discard syscall1(SYS_exit, 1)

  # Get file size using fstat
  var fstat_result: int32 = syscall2(SYS_fstat, fd, cast[int32](stat_buf))
  if fstat_result < 0:
    print_error(cast[ptr uint8]("insmod: cannot stat module file\n"))
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  # Read file size from stat buffer (offset 20 is st_size in 32-bit stat struct)
  var size_ptr: ptr int32 = cast[ptr int32](cast[int32](stat_buf) + 20)
  var module_size: int32 = size_ptr[0]

  # Check if module is too large
  if module_size > 2097152 - 8192:
    print_error(cast[ptr uint8]("insmod: module too large\n"))
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  # Read module data
  var nread: int32 = syscall3(SYS_read, fd, cast[int32](module_data), module_size)
  discard syscall1(SYS_close, fd)

  if nread != module_size:
    print_error(cast[ptr uint8]("insmod: failed to read module\n"))
    discard syscall1(SYS_exit, 1)

  # Insert module
  # int init_module(void *module_image, unsigned long len, const char *param_values);
  var empty_params: ptr uint8 = cast[ptr uint8](old_brk + 2048)
  empty_params[0] = cast[uint8](0)

  var result: int32 = syscall3(SYS_init_module, cast[int32](module_data), module_size, cast[int32](empty_params))

  if result < 0:
    print_error(cast[ptr uint8]("insmod: failed to insert module\n"))
    print_error(cast[ptr uint8]("insmod: are you root? try: sudo insmod\n"))
    print_error(cast[ptr uint8]("insmod: error code: "))
    # Print error code (would need number to string conversion)
    print_error(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 1)

  print(cast[ptr uint8]("Module inserted successfully\n"))
  discard syscall1(SYS_exit, 0)
