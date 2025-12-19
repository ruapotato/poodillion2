# df - Report file system disk space usage
# Reads /proc/mounts and uses statfs syscall to get filesystem info

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_statfs: int32 = 99

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# String utilities
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Print a number
proc print_num(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var buf: ptr uint8 = cast[ptr uint8](0)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  buf = cast[ptr uint8](old_brk)

  var num: int32 = n
  var neg: int32 = 0
  if num < 0:
    neg = 1
    num = 0 - num

  var i: int32 = 0
  while num > 0:
    var digit: int32 = num % 10
    buf[i] = cast[uint8](48 + digit)
    num = num / 10
    i = i + 1

  if neg != 0:
    buf[i] = cast[uint8](45)  # '-'
    i = i + 1

  # Reverse the digits
  var j: int32 = 0
  var k: int32 = i - 1
  while j < k:
    var temp: uint8 = buf[j]
    buf[j] = buf[k]
    buf[k] = temp
    j = j + 1
    k = k - 1

  discard syscall3(SYS_write, STDOUT, cast[int32](buf), i)

# Print with padding
proc print_padded(msg: ptr uint8, width: int32) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)
  var spaces: int32 = width - len
  while spaces > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
    spaces = spaces - 1

# Copy string
proc strcpy(dest: ptr uint8, src: ptr uint8): int32 =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)
  return i

# Compare string with constant
proc str_eq(s: ptr uint8, c: ptr uint8): int32 =
  var i: int32 = 0
  while true:
    if s[i] != c[i]:
      return 0
    if s[i] == cast[uint8](0):
      return 1
    i = i + 1
  return 0

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # old_brk + 0: /proc/mounts buffer (8KB)
  # old_brk + 8192: statfs buffer (512 bytes)
  # old_brk + 8704: mount point buffer (256 bytes)
  # old_brk + 8960: filesystem buffer (256 bytes)
  var mounts_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var statfs_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var mount_point: ptr uint8 = cast[ptr uint8](old_brk + 8704)
  var filesystem: ptr uint8 = cast[ptr uint8](old_brk + 8960)

  # Open /proc/mounts
  var fd: int32 = syscall3(SYS_open, cast[int32]("/proc/mounts"), O_RDONLY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("Error: cannot open /proc/mounts\n"))
    discard syscall1(SYS_exit, 1)

  # Read /proc/mounts
  var nread: int32 = syscall3(SYS_read, fd, cast[int32](mounts_buf), 8192)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print_err(cast[ptr uint8]("Error: cannot read /proc/mounts\n"))
    discard syscall1(SYS_exit, 1)

  # Print header
  print(cast[ptr uint8]("Filesystem           Size       Used      Avail Use% Mounted on\n"))

  # Parse /proc/mounts line by line
  var pos: int32 = 0
  while pos < nread:
    # Parse line: device mountpoint fstype options ...
    # Example: /dev/sda1 / ext4 rw,relatime 0 0

    # Read filesystem name
    var fs_pos: int32 = 0
    while pos < nread and mounts_buf[pos] != cast[uint8](32) and mounts_buf[pos] != cast[uint8](10):
      filesystem[fs_pos] = mounts_buf[pos]
      fs_pos = fs_pos + 1
      pos = pos + 1
    filesystem[fs_pos] = cast[uint8](0)

    # Skip spaces
    while pos < nread and mounts_buf[pos] == cast[uint8](32):
      pos = pos + 1

    # Read mount point
    var mp_pos: int32 = 0
    while pos < nread and mounts_buf[pos] != cast[uint8](32) and mounts_buf[pos] != cast[uint8](10):
      mount_point[mp_pos] = mounts_buf[pos]
      mp_pos = mp_pos + 1
      pos = pos + 1
    mount_point[mp_pos] = cast[uint8](0)

    # Skip rest of line
    while pos < nread and mounts_buf[pos] != cast[uint8](10):
      pos = pos + 1
    pos = pos + 1  # Skip newline

    # Skip empty entries - process only if valid
    if fs_pos > 0 and mp_pos > 0:
      # Get filesystem stats using statfs
      var ret: int32 = syscall2(SYS_statfs, cast[int32](mount_point), cast[int32](statfs_buf))
      if ret >= 0:
        # Parse statfs structure
        # struct statfs {
        #   long f_type;      /* type of file system (offset 0) */
        #   long f_bsize;     /* optimal transfer block size (offset 4) */
        #   long f_blocks;    /* total data blocks (offset 8) */
        #   long f_bfree;     /* free blocks (offset 12) */
        #   long f_bavail;    /* free blocks for unprivileged users (offset 16) */
        #   ...
        # }

        var bsize_ptr: ptr int32 = cast[ptr int32](cast[int32](statfs_buf) + 4)
        var blocks_ptr: ptr int32 = cast[ptr int32](cast[int32](statfs_buf) + 8)
        var bfree_ptr: ptr int32 = cast[ptr int32](cast[int32](statfs_buf) + 12)
        var bavail_ptr: ptr int32 = cast[ptr int32](cast[int32](statfs_buf) + 16)

        var bsize: int32 = bsize_ptr[0]
        var blocks: int32 = blocks_ptr[0]
        var bfree: int32 = bfree_ptr[0]
        var bavail: int32 = bavail_ptr[0]

        # Calculate sizes in KB
        var total_kb: int32 = (blocks * bsize) / 1024
        var free_kb: int32 = (bfree * bsize) / 1024
        var avail_kb: int32 = (bavail * bsize) / 1024
        var used_kb: int32 = total_kb - free_kb

        # Calculate percentage
        var use_pct: int32 = 0
        if total_kb > 0:
          use_pct = (used_kb * 100) / total_kb

        # Print filesystem (20 chars wide)
        print_padded(filesystem, 20)
        discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)

        # Print size (10 chars wide)
        print_num(total_kb)
        discard syscall3(SYS_write, STDOUT, cast[int32]("K"), 1)
        var spaces: int32 = 9
        while spaces > 0:
          discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
          spaces = spaces - 1

        # Print used
        print_num(used_kb)
        discard syscall3(SYS_write, STDOUT, cast[int32]("K"), 1)
        spaces = 9
        while spaces > 0:
          discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
          spaces = spaces - 1

        # Print available
        print_num(avail_kb)
        discard syscall3(SYS_write, STDOUT, cast[int32]("K"), 1)
        spaces = 4
        while spaces > 0:
          discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
          spaces = spaces - 1

        # Print percentage
        print_num(use_pct)
        discard syscall3(SYS_write, STDOUT, cast[int32]("% "), 2)

        # Print mount point
        print(mount_point)
        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  discard syscall1(SYS_exit, 0)
