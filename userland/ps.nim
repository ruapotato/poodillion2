# ps - report process status (structured data output)
# Part of PoodillionOS coreutils
# Outputs binary Process objects, not text!

const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_read: int32 = 3
const SYS_exit: int32 = 1
const SYS_getdents: int32 = 141
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

# Process record (binary format)
# This is what we output - structured data!
proc write_schema_header() =
  # Magic: "PSCH" (Poodillion Schema)
  discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)

  # Version: 1
  var version: uint8 = 1
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)

  # Field count: 3 (pid, memory, name_len for now)
  var field_count: uint8 = 3
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(field_count)), 1)

  # Record size: 12 bytes (4 + 8 + 0)
  var rec_size: uint16 = 12
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(rec_size)), 2)

proc write_process_record(pid: int32, mem: int32) =
  # For now, simple demo: just write pid and placeholder memory
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(pid)), 4)
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(mem)), 4)

  # Placeholder for name length
  var name_len: int32 = 0
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(name_len)), 4)

proc main() =
  # Write schema header
  write_schema_header()

  # Write record count (we'll output a few demo processes)
  var count: int32 = 3
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(count)), 4)

  # Write demo process records (binary)
  write_process_record(1, 1024)
  write_process_record(100, 2048)
  write_process_record(200, 4096)

  discard syscall1(SYS_exit, 0)
