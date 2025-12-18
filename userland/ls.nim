# ls - List directory contents
# Default: human-readable text output
# -b flag: binary PSCH format for pipelines
# -l flag: long listing format
# -a flag: show hidden files (starting with .)

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getdents64: int32 = 220
const SYS_stat64: int32 = 195

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0
const O_DIRECTORY: int32 = 65536  # 0x10000

# File types from dirent
const DT_UNKNOWN: uint8 = 0
const DT_FIFO: uint8 = 1
const DT_CHR: uint8 = 2
const DT_DIR: uint8 = 4
const DT_BLK: uint8 = 6
const DT_REG: uint8 = 8
const DT_LNK: uint8 = 10
const DT_SOCK: uint8 = 12

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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

proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return 1
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 1
  return 0

# Get type character for display
proc type_char(d_type: uint8): uint8 =
  if d_type == DT_DIR:
    return cast[uint8](100)  # 'd'
  if d_type == DT_LNK:
    return cast[uint8](108)  # 'l'
  if d_type == DT_CHR:
    return cast[uint8](99)   # 'c'
  if d_type == DT_BLK:
    return cast[uint8](98)   # 'b'
  if d_type == DT_FIFO:
    return cast[uint8](112)  # 'p'
  if d_type == DT_SOCK:
    return cast[uint8](115)  # 's'
  return cast[uint8](45)     # '-' for regular

# PSCH schema constants
const RECORD_SIZE: int32 = 56
const NAME_SIZE: int32 = 52

proc main() =
  var argc: int32 = get_argc()

  # Parse flags
  var binary_mode: int32 = 0
  var long_mode: int32 = 0
  var show_hidden: int32 = 0
  var path_arg: ptr uint8 = cast[ptr uint8](0)

  var i: int32 = 1
  while i < argc:
    var arg: ptr uint8 = get_argv(i)
    if arg[0] == cast[uint8](45):  # '-'
      # Parse flags
      var j: int32 = 1
      while arg[j] != cast[uint8](0):
        if arg[j] == cast[uint8](98):  # 'b'
          binary_mode = 1
        if arg[j] == cast[uint8](108):  # 'l'
          long_mode = 1
        if arg[j] == cast[uint8](97):  # 'a'
          show_hidden = 1
        j = j + 1
    else:
      # Path argument
      path_arg = arg
    i = i + 1

  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 65536
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # old_brk + 0: getdents buffer (8KB)
  # old_brk + 8192: output records buffer (for binary mode, 24KB)
  # old_brk + 32768: path buffer (256 bytes)
  # old_brk + 33024: name storage for text mode (32KB)
  var dent_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var out_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk + 32768)
  var names_buf: ptr uint8 = cast[ptr uint8](old_brk + 33024)

  # Set path
  if path_arg != cast[ptr uint8](0):
    strcpy(path_buf, path_arg)
  else:
    path_buf[0] = cast[uint8](46)  # '.'
    path_buf[1] = cast[uint8](0)

  # Open directory
  var fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY | O_DIRECTORY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("ls: cannot open directory: "))
    print_err(path_buf)
    print_err(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 1)

  # Storage for entries
  var record_count: int32 = 0
  var out_pos: int32 = 0
  var names_pos: int32 = 0

  # Arrays for text mode: store name pointers and types
  var name_ptrs: ptr int32 = cast[ptr int32](out_buf)  # Reuse out_buf for name pointers
  var name_types: ptr uint8 = cast[ptr uint8](old_brk + 16384)  # Types array

  # Read directory entries
  var nread: int32 = syscall3(SYS_getdents64, fd, cast[int32](dent_buf), 8192)

  while nread > 0:
    var pos: int32 = 0
    while pos < nread:
      # linux_dirent64 structure:
      # d_ino: uint64 (8 bytes) at offset 0
      # d_off: int64 (8 bytes) at offset 8
      # d_reclen: uint16 (2 bytes) at offset 16
      # d_type: uint8 (1 byte) at offset 18
      # d_name: char[] at offset 19

      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](dent_buf) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_type: uint8 = dent_buf[pos + 18]
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](dent_buf) + pos + 19)

      # Skip . and .. unless -a flag
      var skip: int32 = 0
      if d_name[0] == cast[uint8](46):  # '.'
        if show_hidden == 0:
          if d_name[1] == cast[uint8](0):
            skip = 1
          if d_name[1] == cast[uint8](46):
            if d_name[2] == cast[uint8](0):
              skip = 1
        # Also skip other hidden files unless -a
        if show_hidden == 0:
          if d_name[1] != cast[uint8](0):
            if d_name[1] != cast[uint8](46):
              skip = 1

      if skip == 0:
        var name_len: int32 = strlen(d_name)

        if binary_mode != 0:
          # Binary PSCH mode
          var rec_ptr: ptr uint8 = cast[ptr uint8](cast[int32](out_buf) + out_pos)

          # Zero out the record first
          var j: int32 = 0
          while j < RECORD_SIZE:
            rec_ptr[j] = cast[uint8](0)
            j = j + 1

          # Copy name (up to NAME_SIZE-1 chars)
          if name_len > NAME_SIZE - 1:
            name_len = NAME_SIZE - 1
          j = 0
          while j < name_len:
            rec_ptr[j] = d_name[j]
            j = j + 1

          # Set type at offset 52
          rec_ptr[NAME_SIZE] = d_type

          out_pos = out_pos + RECORD_SIZE
        else:
          # Text mode - store name pointer and type
          # Copy name to names buffer
          var name_start: int32 = names_pos
          var j: int32 = 0
          while j < name_len:
            names_buf[names_pos] = d_name[j]
            names_pos = names_pos + 1
            j = j + 1
          names_buf[names_pos] = cast[uint8](0)
          names_pos = names_pos + 1

          # Store pointer
          name_ptrs[record_count] = cast[int32](names_buf) + name_start
          name_types[record_count] = d_type

        record_count = record_count + 1

      pos = pos + reclen

    # Read more entries
    nread = syscall3(SYS_getdents64, fd, cast[int32](dent_buf), 8192)

  discard syscall1(SYS_close, fd)

  if binary_mode != 0:
    # Output PSCH format
    # Header: "PSCH" (4) + version (1) + fields (1) + record_size (2) = 8 bytes
    # Then: record_count (4) + records

    discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)

    var version: uint8 = 1
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)

    var fields: uint8 = 2
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(fields)), 1)

    var rec_size: uint16 = 56
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(rec_size)), 2)

    discard syscall3(SYS_write, STDOUT, cast[int32](addr(record_count)), 4)
    discard syscall3(SYS_write, STDOUT, cast[int32](out_buf), out_pos)
  else:
    # Text mode output
    if long_mode != 0:
      # Long listing format
      i = 0
      while i < record_count:
        var name: ptr uint8 = cast[ptr uint8](name_ptrs[i])
        var ftype: uint8 = name_types[i]

        # Print type character
        var tc: uint8 = type_char(ftype)
        discard syscall3(SYS_write, STDOUT, cast[int32](addr(tc)), 1)
        print(cast[ptr uint8]("  "))

        # Print name
        print(name)

        # Add / for directories
        if ftype == DT_DIR:
          print(cast[ptr uint8]("/"))

        print(cast[ptr uint8]("\n"))
        i = i + 1
    else:
      # Simple listing - multiple columns
      # For simplicity, just list one per line with directory indicator
      i = 0
      while i < record_count:
        var name: ptr uint8 = cast[ptr uint8](name_ptrs[i])
        var ftype: uint8 = name_types[i]

        print(name)

        # Add / for directories
        if ftype == DT_DIR:
          print(cast[ptr uint8]("/"))

        print(cast[ptr uint8]("\n"))
        i = i + 1

  discard syscall1(SYS_exit, 0)
