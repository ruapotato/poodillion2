# ps - List processes as structured data (REAL /proc parsing!)
# Schema: pid(4) + ppid(4) + state(1) + pad(3) + rss(4) + name(32) = 48 bytes/record

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getdents64: int32 = 220

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

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Check if string is all digits (a PID directory)
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
  # Skip leading whitespace
  while s[i] == cast[uint8](32):
    i = i + 1
  # Handle negative
  var neg: int32 = 0
  if s[i] == cast[uint8](45):  # '-'
    neg = 1
    i = i + 1
  while s[i] >= cast[uint8](48):
    if s[i] > cast[uint8](57):
      break
    result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  if neg == 1:
    result = 0 - result
  return result

# Build path: /proc/PID/stat
proc build_stat_path(path: ptr uint8, pid_str: ptr uint8) =
  # /proc/
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
  # /stat
  path[pos] = cast[uint8](47)      # /
  path[pos + 1] = cast[uint8](115) # s
  path[pos + 2] = cast[uint8](116) # t
  path[pos + 3] = cast[uint8](97)  # a
  path[pos + 4] = cast[uint8](116) # t
  path[pos + 5] = cast[uint8](0)

# Schema constants
const RECORD_SIZE: int32 = 48
const NAME_SIZE: int32 = 32

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 131072
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # +0: dent buffer (8KB)
  # +8192: output records (64KB)
  # +73728: stat file buffer (4KB)
  # +77824: path buffer (256 bytes)
  var dent_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var out_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var stat_buf: ptr uint8 = cast[ptr uint8](old_brk + 73728)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk + 77824)

  # Open /proc
  path_buf[0] = cast[uint8](47)   # /
  path_buf[1] = cast[uint8](112)  # p
  path_buf[2] = cast[uint8](114)  # r
  path_buf[3] = cast[uint8](111)  # o
  path_buf[4] = cast[uint8](99)   # c
  path_buf[5] = cast[uint8](0)

  var proc_fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY | O_DIRECTORY, 0)
  if proc_fd < 0:
    print_err(cast[ptr uint8]("Error: cannot open /proc\n"))
    discard syscall1(SYS_exit, 1)

  var record_count: int32 = 0
  var out_pos: int32 = 0

  # Read /proc directory
  var nread: int32 = syscall3(SYS_getdents64, proc_fd, cast[int32](dent_buf), 8192)

  while nread > 0:
    var pos: int32 = 0
    while pos < nread:
      # Parse dirent64
      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](dent_buf) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](dent_buf) + pos + 19)

      # Check if this is a PID directory (all numeric)
      if is_numeric(d_name) == 1:
        # Build path to /proc/PID/stat
        build_stat_path(path_buf, d_name)

        # Open and read stat file
        var stat_fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY, 0)
        if stat_fd >= 0:
          var stat_len: int32 = syscall3(SYS_read, stat_fd, cast[int32](stat_buf), 4095)
          discard syscall1(SYS_close, stat_fd)

          if stat_len > 0:
            stat_buf[stat_len] = cast[uint8](0)

            # Parse /proc/PID/stat format:
            # pid (comm) state ppid pgrp session tty_nr tpgid flags
            # minflt cminflt majflt cmajflt utime stime cutime cstime
            # priority nice num_threads itrealvalue starttime vsize rss ...

            # Get PID (first field)
            var pid: int32 = parse_int(stat_buf)

            # Find comm (in parentheses)
            var comm_start: int32 = 0
            var i: int32 = 0
            while stat_buf[i] != cast[uint8](0):
              if stat_buf[i] == cast[uint8](40):  # '('
                comm_start = i + 1
                break
              i = i + 1

            # Find the LAST ')' to handle names like ((sd-pam))
            var comm_end: int32 = comm_start
            var last_paren: int32 = comm_start
            while stat_buf[comm_end] != cast[uint8](0):
              if stat_buf[comm_end] == cast[uint8](41):  # ')'
                last_paren = comm_end
              comm_end = comm_end + 1
            comm_end = last_paren

            # Find state (after closing paren)
            var state_pos: int32 = comm_end + 2  # skip ") "
            var state: uint8 = stat_buf[state_pos]

            # Find ppid (4th field, after state)
            var field_pos: int32 = state_pos + 2  # skip "S "
            var ppid: int32 = parse_int(cast[ptr uint8](cast[int32](stat_buf) + field_pos))

            # Skip to field 24 (rss) - count spaces
            var field_num: int32 = 4
            i = field_pos
            while field_num < 24:
              if stat_buf[i] == cast[uint8](32):  # space
                field_num = field_num + 1
              i = i + 1
              if stat_buf[i] == cast[uint8](0):
                break
            var rss: int32 = parse_int(cast[ptr uint8](cast[int32](stat_buf) + i))
            # RSS is in pages, convert to KB (assume 4KB pages)
            rss = rss * 4

            # Build output record
            var rec: ptr uint8 = cast[ptr uint8](cast[int32](out_buf) + out_pos)

            # Zero out record
            var j: int32 = 0
            while j < RECORD_SIZE:
              rec[j] = cast[uint8](0)
              j = j + 1

            # pid at offset 0 (4 bytes)
            var pid_ptr: ptr int32 = cast[ptr int32](rec)
            pid_ptr[0] = pid

            # ppid at offset 4 (4 bytes)
            var ppid_ptr: ptr int32 = cast[ptr int32](cast[int32](rec) + 4)
            ppid_ptr[0] = ppid

            # state at offset 8 (1 byte)
            rec[8] = state

            # padding at offset 9-11 (3 bytes) - already zeroed

            # rss at offset 12 (4 bytes)
            var rss_ptr: ptr int32 = cast[ptr int32](cast[int32](rec) + 12)
            rss_ptr[0] = rss

            # name at offset 16 (32 bytes)
            var name_len: int32 = comm_end - comm_start
            if name_len > NAME_SIZE - 1:
              name_len = NAME_SIZE - 1
            j = 0
            while j < name_len:
              rec[16 + j] = stat_buf[comm_start + j]
              j = j + 1

            out_pos = out_pos + RECORD_SIZE
            record_count = record_count + 1

      pos = pos + reclen

    nread = syscall3(SYS_getdents64, proc_fd, cast[int32](dent_buf), 8192)

  discard syscall1(SYS_close, proc_fd)

  # Output PSCH format
  # Magic
  discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)

  # Version
  var version: uint8 = 1
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)

  # Fields: 5 (pid, ppid, state, rss, name)
  var fields: uint8 = 5
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(fields)), 1)

  # Record size
  var rec_size: uint16 = 48
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(rec_size)), 2)

  # Record count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(record_count)), 4)

  # Output records
  discard syscall3(SYS_write, STDOUT, cast[int32](out_buf), out_pos)

  discard syscall1(SYS_exit, 0)
