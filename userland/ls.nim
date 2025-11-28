# ls - List directory contents as structured data
# Outputs PSCH format: name(52) + type(1) + pad(3) = 56 bytes/record

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

# String length
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

# Print to stderr
proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Schema: 52-byte name + 1-byte type + 3-byte padding = 56 bytes per record
const RECORD_SIZE: int32 = 56
const NAME_SIZE: int32 = 52

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32768
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # old_brk + 0: getdents buffer (8KB)
  # old_brk + 8192: output records buffer (16KB)
  # old_brk + 24576: path buffer (256 bytes)
  var dent_buf: ptr uint8 = cast[ptr uint8](old_brk)
  var out_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var path_buf: ptr uint8 = cast[ptr uint8](old_brk + 24576)

  # Default to current directory
  path_buf[0] = cast[uint8](46)  # '.'
  path_buf[1] = cast[uint8](0)

  # Open directory
  var fd: int32 = syscall3(SYS_open, cast[int32](path_buf), O_RDONLY | O_DIRECTORY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("Error: cannot open directory\n"))
    discard syscall1(SYS_exit, 1)

  # Count entries first (we need record count for header)
  var record_count: int32 = 0
  var out_pos: int32 = 0

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

      # Skip . and ..
      var skip: int32 = 0
      if d_name[0] == cast[uint8](46):  # '.'
        if d_name[1] == cast[uint8](0):
          skip = 1
        if d_name[1] == cast[uint8](46):
          if d_name[2] == cast[uint8](0):
            skip = 1

      if skip == 0:
        # Build output record
        var rec_ptr: ptr uint8 = cast[ptr uint8](cast[int32](out_buf) + out_pos)

        # Zero out the record first
        var j: int32 = 0
        while j < RECORD_SIZE:
          rec_ptr[j] = cast[uint8](0)
          j = j + 1

        # Copy name (up to NAME_SIZE-1 chars)
        var name_len: int32 = strlen(d_name)
        if name_len > NAME_SIZE - 1:
          name_len = NAME_SIZE - 1
        j = 0
        while j < name_len:
          rec_ptr[j] = d_name[j]
          j = j + 1

        # Set type at offset 52
        rec_ptr[NAME_SIZE] = d_type

        out_pos = out_pos + RECORD_SIZE
        record_count = record_count + 1

      pos = pos + reclen

    # Read more entries
    nread = syscall3(SYS_getdents64, fd, cast[int32](dent_buf), 8192)

  discard syscall1(SYS_close, fd)

  # Now output PSCH format
  # Header: "PSCH" (4) + version (1) + fields (1) + record_size (2) = 8 bytes
  # Then: record_count (4) + records

  # Magic: PSCH
  discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)

  # Version: 1
  var version: uint8 = 1
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)

  # Fields: 2 (name, type)
  var fields: uint8 = 2
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(fields)), 1)

  # Record size: 56
  var rec_size: uint16 = 56
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(rec_size)), 2)

  # Record count
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(record_count)), 4)

  # Output all records
  discard syscall3(SYS_write, STDOUT, cast[int32](out_buf), out_pos)

  discard syscall1(SYS_exit, 0)
