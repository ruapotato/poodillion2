# ps - List processes
# Default: human-readable text output
# -b flag: binary PSCH format for pipelines
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
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

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

# Print number with padding
proc print_num_pad(n: int32, width: int32) =
  # First calculate number of digits
  var temp: int32 = n
  var digits: int32 = 0
  if n == 0:
    digits = 1
  else:
    if n < 0:
      temp = 0 - n
    while temp > 0:
      digits = digits + 1
      temp = temp / 10

  # Print padding spaces
  var pad: int32 = width - digits
  if n < 0:
    pad = pad - 1
  while pad > 0:
    print(cast[ptr uint8](" "))
    pad = pad - 1

  # Print the number
  if n < 0:
    print(cast[ptr uint8]("-"))
    temp = 0 - n
  else:
    temp = n

  if temp == 0:
    print(cast[ptr uint8]("0"))
  else:
    # Build digits in reverse
    var buf: ptr uint8 = cast[ptr uint8](0)
    var old_brk: int32 = syscall1(SYS_brk, 0)
    discard syscall1(SYS_brk, old_brk + 32)
    buf = cast[ptr uint8](old_brk)
    var pos: int32 = 0
    while temp > 0:
      buf[pos] = cast[uint8](48 + temp % 10)
      pos = pos + 1
      temp = temp / 10
    # Print in reverse
    while pos > 0:
      pos = pos - 1
      discard syscall3(SYS_write, STDOUT, cast[int32](buf) + pos, 1)

proc is_numeric(s: ptr uint8): int32 =
  var i: int32 = 0
  if s[0] == cast[uint8](0):
    return 0
  while s[i] != cast[uint8](0):
    if s[i] < cast[uint8](48):
      return 0
    if s[i] > cast[uint8](57):
      return 0
    i = i + 1
  return 1

proc parse_int(s: ptr uint8): int32 =
  var result: int32 = 0
  var i: int32 = 0
  while s[i] == cast[uint8](32):
    i = i + 1
  var neg: int32 = 0
  if s[i] == cast[uint8](45):
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

proc build_stat_path(path: ptr uint8, pid_str: ptr uint8) =
  path[0] = cast[uint8](47)
  path[1] = cast[uint8](112)
  path[2] = cast[uint8](114)
  path[3] = cast[uint8](111)
  path[4] = cast[uint8](99)
  path[5] = cast[uint8](47)
  var pos: int32 = 6
  var i: int32 = 0
  while pid_str[i] != cast[uint8](0):
    path[pos] = pid_str[i]
    pos = pos + 1
    i = i + 1
  path[pos] = cast[uint8](47)
  path[pos + 1] = cast[uint8](115)
  path[pos + 2] = cast[uint8](116)
  path[pos + 3] = cast[uint8](97)
  path[pos + 4] = cast[uint8](116)
  path[pos + 5] = cast[uint8](0)

const RECORD_SIZE: int32 = 48
const NAME_SIZE: int32 = 32

proc main() =
  var argc: int32 = get_argc()
  var binary_mode: int32 = 0

  var i: int32 = 1
  while i < argc:
    var arg: ptr uint8 = get_argv(i)
    if arg[0] == cast[uint8](45):
      var j: int32 = 1
      while arg[j] != cast[uint8](0):
        if arg[j] == cast[uint8](98):
          binary_mode = 1
        j = j + 1
    i = i + 1

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 131072
  discard syscall1(SYS_brk, new_brk)

  var dent_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var out_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var stat_buf: ptr uint8 = cast[ptr uint8](old_brk + 73728)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk + 77824)

  # For text mode, store process info
  var pids: ptr int32 = cast[ptr int32](old_brk + 78080)
  var ppids: ptr int32 = cast[ptr int32](old_brk + 82176)
  var states: ptr uint8 = cast[ptr uint8](old_brk + 86272)
  var rsss: ptr int32 = cast[ptr int32](old_brk + 90368)
  var names: ptr uint8 = cast[ptr uint8](old_brk + 94464)

  path_buf[0] = cast[uint8](47)
  path_buf[1] = cast[uint8](112)
  path_buf[2] = cast[uint8](114)
  path_buf[3] = cast[uint8](111)
  path_buf[4] = cast[uint8](99)
  path_buf[5] = cast[uint8](0)

  var proc_fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY | O_DIRECTORY, 0)
  if proc_fd < 0:
    print_err(cast[ptr uint8]("ps: cannot open /proc\n"))
    discard syscall1(SYS_exit, 1)

  var record_count: int32 = 0
  var out_pos: int32 = 0
  var names_pos: int32 = 0

  var nread: int32 = syscall3(SYS_getdents64, proc_fd, cast[int32](dent_buf), 8192)

  while nread > 0:
    var pos: int32 = 0
    while pos < nread:
      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](dent_buf) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](dent_buf) + pos + 19)

      if is_numeric(d_name) == 1:
        build_stat_path(path_buf, d_name)

        var stat_fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY, 0)
        if stat_fd >= 0:
          var stat_len: int32 = syscall3(SYS_read, stat_fd, cast[int32](stat_buf), 4095)
          discard syscall1(SYS_close, stat_fd)

          if stat_len > 0:
            stat_buf[stat_len] = cast[uint8](0)

            var pid: int32 = parse_int(stat_buf)

            var comm_start: int32 = 0
            i = 0
            while stat_buf[i] != cast[uint8](0):
              if stat_buf[i] == cast[uint8](40):
                comm_start = i + 1
                break
              i = i + 1

            var comm_end: int32 = comm_start
            var last_paren: int32 = comm_start
            while stat_buf[comm_end] != cast[uint8](0):
              if stat_buf[comm_end] == cast[uint8](41):
                last_paren = comm_end
              comm_end = comm_end + 1
            comm_end = last_paren

            var state_pos: int32 = comm_end + 2
            var state: uint8 = stat_buf[state_pos]

            var field_pos: int32 = state_pos + 2
            var ppid: int32 = parse_int(cast[ptr uint8](cast[int32](stat_buf) + field_pos))

            var field_num: int32 = 4
            i = field_pos
            while field_num < 24:
              if stat_buf[i] == cast[uint8](32):
                field_num = field_num + 1
              i = i + 1
              if stat_buf[i] == cast[uint8](0):
                break
            var rss: int32 = parse_int(cast[ptr uint8](cast[int32](stat_buf) + i))
            rss = rss * 4

            if binary_mode != 0:
              var rec: ptr uint8 = cast[ptr uint8](cast[int32](out_buf) + out_pos)
              var j: int32 = 0
              while j < RECORD_SIZE:
                rec[j] = cast[uint8](0)
                j = j + 1
              var pid_ptr: ptr int32 = cast[ptr int32](rec)
              pid_ptr[0] = pid
              var ppid_ptr: ptr int32 = cast[ptr int32](cast[int32](rec) + 4)
              ppid_ptr[0] = ppid
              rec[8] = state
              var rss_ptr: ptr int32 = cast[ptr int32](cast[int32](rec) + 12)
              rss_ptr[0] = rss
              var name_len: int32 = comm_end - comm_start
              if name_len > NAME_SIZE - 1:
                name_len = NAME_SIZE - 1
              j = 0
              while j < name_len:
                rec[16 + j] = stat_buf[comm_start + j]
                j = j + 1
              out_pos = out_pos + RECORD_SIZE
            else:
              # Text mode - store info
              pids[record_count] = pid
              ppids[record_count] = ppid
              states[record_count] = state
              rsss[record_count] = rss

              # Copy name
              var name_len: int32 = comm_end - comm_start
              if name_len > NAME_SIZE - 1:
                name_len = NAME_SIZE - 1
              var j: int32 = 0
              while j < name_len:
                names[names_pos + j] = stat_buf[comm_start + j]
                j = j + 1
              names[names_pos + name_len] = cast[uint8](0)
              names_pos = names_pos + NAME_SIZE

            record_count = record_count + 1

      pos = pos + reclen

    nread = syscall3(SYS_getdents64, proc_fd, cast[int32](dent_buf), 8192)

  discard syscall1(SYS_close, proc_fd)

  if binary_mode != 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)
    var version: uint8 = 1
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)
    var fields: uint8 = 5
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(fields)), 1)
    var rec_size: uint16 = 48
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(rec_size)), 2)
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(record_count)), 4)
    discard syscall3(SYS_write, STDOUT, cast[int32](out_buf), out_pos)
  else:
    # Text mode output - header
    print(cast[ptr uint8]("  PID  PPID S   RSS COMMAND\n"))

    i = 0
    while i < record_count:
      print_num_pad(pids[i], 5)
      print(cast[ptr uint8](" "))
      print_num_pad(ppids[i], 5)
      print(cast[ptr uint8](" "))
      discard syscall3(SYS_write, STDOUT, cast[int32](addr(states[i])), 1)
      print(cast[ptr uint8](" "))
      print_num_pad(rsss[i], 5)
      print(cast[ptr uint8](" "))
      print(cast[ptr uint8](cast[int32](names) + i * NAME_SIZE))
      print(cast[ptr uint8]("\n"))
      i = i + 1

  discard syscall1(SYS_exit, 0)
