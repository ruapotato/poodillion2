# lsof - List open files (simplified)
# Shows open file descriptors for all processes
# Format: COMMAND PID USER FD TYPE NAME

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getdents64: int32 = 220
const SYS_readlink: int32 = 85

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2
const O_RDONLY: int32 = 0
const O_DIRECTORY: int32 = 65536

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

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

# Check if string is all digits
proc is_numeric(s: ptr uint8): int32 =
  var i: int32 = 0
  if s[0] == cast[uint8](0):
    return 0
  while s[i] != cast[uint8](0):
    if s[i] < cast[uint8](48):  # '0'
      return 0
    if s[i] > cast[uint8](57):  # '9'
      return 0
    i = i + 1
  return 1

# Parse integer from string
proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] >= cast[uint8](48):
    if s[i] > cast[uint8](57):
      break
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n

  if num < 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("-"), 1)
    num = 0 - num

  # Count digits and reverse
  var temp: int32 = 0
  var digits: int32 = 0
  while num > 0:
    temp = temp * 10 + (num % 10)
    num = num / 10
    digits = digits + 1

  # Print digits
  while digits > 0:
    var d: uint8 = cast[uint8](48 + (temp % 10))
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(d)), 1)
    temp = temp / 10
    digits = digits - 1

# Print string with padding
proc print_str_padded(s: ptr uint8, width: int32) =
  var len: int32 = strlen(s)

  # Print string
  discard syscall3(SYS_write, STDOUT, cast[int32](s), len)

  # Print padding spaces
  var spaces: int32 = width - len
  while spaces > 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](" "), 1)
    spaces = spaces - 1

# Build path: /proc/PID/comm
proc build_comm_path(path: ptr uint8, pid_str: ptr uint8) =
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  var pos: int32 = 6
  # Copy PID
  var i: int32 = 0
  while pid_str[i] != cast[uint8](0):
    path[pos] = pid_str[i]
    pos = pos + 1
    i = i + 1
  # /comm
  path[pos] = cast[uint8](47)      # /
  path[pos + 1] = cast[uint8](99)  # c
  path[pos + 2] = cast[uint8](111) # o
  path[pos + 3] = cast[uint8](109) # m
  path[pos + 4] = cast[uint8](109) # m
  path[pos + 5] = cast[uint8](0)

# Build path: /proc/PID/fd
proc build_fd_path(path: ptr uint8, pid_str: ptr uint8) =
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  var pos: int32 = 6
  # Copy PID
  var i: int32 = 0
  while pid_str[i] != cast[uint8](0):
    path[pos] = pid_str[i]
    pos = pos + 1
    i = i + 1
  # /fd
  path[pos] = cast[uint8](47)     # /
  path[pos + 1] = cast[uint8](102) # f
  path[pos + 2] = cast[uint8](100) # d
  path[pos + 3] = cast[uint8](0)

# Build path: /proc/PID/fd/FD
proc build_fd_link_path(path: ptr uint8, pid_str: ptr uint8, fd_str: ptr uint8) =
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  var pos: int32 = 6
  # Copy PID
  var i: int32 = 0
  while pid_str[i] != cast[uint8](0):
    path[pos] = pid_str[i]
    pos = pos + 1
    i = i + 1
  # /fd/
  path[pos] = cast[uint8](47)     # /
  path[pos + 1] = cast[uint8](102) # f
  path[pos + 2] = cast[uint8](100) # d
  path[pos + 3] = cast[uint8](47)  # /
  pos = pos + 4
  # Copy FD
  i = 0
  while fd_str[i] != cast[uint8](0):
    path[pos] = fd_str[i]
    pos = pos + 1
    i = i + 1
  path[pos] = cast[uint8](0)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 65536
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # +0: proc dent buffer (8KB)
  # +8192: fd dent buffer (8KB)
  # +16384: comm buffer (256 bytes)
  # +16640: path buffer (512 bytes)
  # +17152: link target buffer (512 bytes)
  var proc_dent_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var fd_dent_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var comm_buf: ptr uint8 = cast[ptr uint8](old_brk + 16384)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk + 16640)
  var link_buf: ptr uint8 = cast[ptr uint8](old_brk + 17152)

  # Print header
  print(cast[ptr uint8]("COMMAND          PID    FD   TYPE   NAME\n"))

  # Open /proc
  path_buf[0] = cast[uint8](47)   # /
  path_buf[1] = cast[uint8](112)  # p
  path_buf[2] = cast[uint8](114)  # r
  path_buf[3] = cast[uint8](111)  # o
  path_buf[4] = cast[uint8](99)   # c
  path_buf[5] = cast[uint8](0)

  var proc_fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY | O_DIRECTORY, 0)
  if proc_fd < 0:
    print_err(cast[ptr uint8]("lsof: cannot open /proc\n"))
    discard syscall1(SYS_exit, 1)

  # Read /proc directory
  var nread: int32 = syscall3(SYS_getdents64, proc_fd, cast[int32](proc_dent_buf), 8192)

  while nread > 0:
    var pos: int32 = 0
    while pos < nread:
      # Parse dirent64
      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](proc_dent_buf) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](proc_dent_buf) + pos + 19)

      # Check if this is a PID directory (all numeric)
      if is_numeric(d_name) == 1:
        var pid: int32 = parse_int(d_name)

        # Get process command name
        build_comm_path(path_buf, d_name)
        var comm_fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY, 0)
        var comm_len: int32 = 0
        if comm_fd >= 0:
          comm_len = syscall3(SYS_read, comm_fd, cast[int32](comm_buf), 255)
          discard syscall1(SYS_close, comm_fd)
          if comm_len > 0:
            # Remove trailing newline
            if comm_buf[comm_len - 1] == cast[uint8](10):
              comm_len = comm_len - 1
            comm_buf[comm_len] = cast[uint8](0)
          else:
            comm_buf[0] = cast[uint8](63)  # '?'
            comm_buf[1] = cast[uint8](0)
        else:
          comm_buf[0] = cast[uint8](63)  # '?'
          comm_buf[1] = cast[uint8](0)

        # Open /proc/PID/fd directory
        build_fd_path(path_buf, d_name)
        var fd_dir: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY | O_DIRECTORY, 0)

        if fd_dir >= 0:
          # Read fd directory
          var fd_nread: int32 = syscall3(SYS_getdents64, fd_dir, cast[int32](fd_dent_buf), 8192)

          while fd_nread > 0:
            var fd_pos: int32 = 0
            while fd_pos < fd_nread:
              var fd_reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](fd_dent_buf) + fd_pos + 16)
              var fd_reclen: int32 = cast[int32](fd_reclen_ptr[0])
              var fd_name: ptr uint8 = cast[ptr uint8](cast[int32](fd_dent_buf) + fd_pos + 19)

              # Check if this is a numeric fd entry
              if is_numeric(fd_name) == 1:
                # Build path to /proc/PID/fd/FD
                build_fd_link_path(path_buf, d_name, fd_name)

                # Read the symlink target
                var link_len: int32 = syscall3(SYS_readlink, cast[int32](path_buf), cast[int32](link_buf), 511)
                if link_len > 0:
                  link_buf[link_len] = cast[uint8](0)
                else:
                  link_buf[0] = cast[uint8](63)  # '?'
                  link_buf[1] = cast[uint8](0)

                # Print: COMMAND PID FD TYPE NAME
                print_str_padded(comm_buf, 16)
                print(cast[ptr uint8](" "))
                print_int(pid)
                print(cast[ptr uint8]("    "))
                print(fd_name)
                print(cast[ptr uint8]("    REG    "))
                print(link_buf)
                print(cast[ptr uint8]("\n"))

              fd_pos = fd_pos + fd_reclen

            fd_nread = syscall3(SYS_getdents64, fd_dir, cast[int32](fd_dent_buf), 8192)

          discard syscall1(SYS_close, fd_dir)

      pos = pos + reclen

    nread = syscall3(SYS_getdents64, proc_fd, cast[int32](proc_dent_buf), 8192)

  discard syscall1(SYS_close, proc_fd)

  discard syscall1(SYS_exit, 0)
