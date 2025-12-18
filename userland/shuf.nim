# shuf - Shuffle lines randomly
# Usage: shuf [FILE]
# Randomly permute lines from FILE or stdin
# Uses simple LCG random number generator
# Part of PoodillionOS math utilities

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_time: int32 = 13

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

# Global random state
var rand_state: uint32

# Print error
proc print_err(msg: ptr uint8, len: int32) =
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Initialize random number generator
proc init_rand() =
  # Try to read from /dev/urandom
  var urandom_fd: int32 = syscall2(SYS_open, cast[int32]("/dev/urandom"), O_RDONLY)

  if urandom_fd >= 0:
    # Read 4 bytes for seed - allocate on heap
    var old_brk: int32 = syscall1(SYS_brk, 0)
    var new_brk: int32 = old_brk + 16
    discard syscall1(SYS_brk, new_brk)
    var seed_buf: ptr int32 = cast[ptr int32](old_brk)

    var n: int32 = syscall3(SYS_read, urandom_fd, cast[int32](seed_buf), 4)
    if n == 4:
      rand_state = cast[uint32](seed_buf[0])
    discard syscall1(SYS_close, urandom_fd)
  else:
    # Fallback to time
    var t: int32 = syscall1(SYS_time, 0)
    rand_state = cast[uint32](t)

  # Ensure non-zero seed
  if rand_state == cast[uint32](0):
    rand_state = cast[uint32](12345)

# Linear Congruential Generator
# Using constants from glibc: a=1103515245, c=12345, m=2^31
proc random(): uint32 =
  rand_state = (cast[uint32](1103515245) * rand_state + cast[uint32](12345)) & cast[uint32](2147483647)
  return rand_state

# Random number in range [0, n)
proc random_range(n: uint32): uint32 =
  if n == cast[uint32](0):
    return cast[uint32](0)
  return random() % n

# Swap two line pointers
proc swap_lines(lines: ptr uint32, i: int32, j: int32) =
  var temp: uint32 = lines[i]
  lines[i] = lines[j]
  lines[j] = temp

# Fisher-Yates shuffle
proc shuffle_array(lines: ptr uint32, count: int32) =
  var i: int32 = count - 1
  while i > 0:
    var j: uint32 = random_range(cast[uint32](i + 1))
    swap_lines(lines, i, cast[int32](j))
    i = i - 1

# Read all input and store line pointers
proc read_and_shuffle(fd: int32) =
  # Allocate large buffer for input (64KB)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 65536
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  # Read all input
  var total: int32 = 0
  var running: int32 = 1

  while running != 0:
    var n: int32 = syscall3(SYS_read, fd, cast[int32](buffer + total), 65536 - total)
    if n <= 0:
      running = 0
    else:
      total = total + n
      if total >= 65536:
        running = 0  # Buffer full, stop reading

  if total == 0:
    discard syscall1(SYS_exit, 0)

  # Count lines and store pointers
  # Allocate space for line pointers (max 4096 lines)
  old_brk = syscall1(SYS_brk, 0)
  new_brk = old_brk + 16384  # 4096 * 4 bytes
  discard syscall1(SYS_brk, new_brk)
  var line_ptrs: ptr uint32 = cast[ptr uint32](old_brk)

  var line_count: int32 = 0
  var line_start: int32 = 0
  var i: int32 = 0

  while i < total:
    if buffer[i] == cast[uint8](10):  # newline
      # Store line pointer (offset from buffer)
      line_ptrs[line_count] = cast[uint32](line_start)
      line_count = line_count + 1
      line_start = i + 1

      if line_count >= 4096:
        break  # Max lines reached
    i = i + 1

  # Handle last line if no trailing newline
  if line_start < total:
    if line_count < 4096:
      line_ptrs[line_count] = cast[uint32](line_start)
      line_count = line_count + 1

  # Shuffle line pointers
  shuffle_array(line_ptrs, line_count)

  # Output shuffled lines
  var j: int32 = 0
  while j < line_count:
    var start: int32 = cast[int32](line_ptrs[j])
    var end: int32 = start

    # Find end of line
    while end < total and buffer[end] != cast[uint8](10):
      end = end + 1

    # Write line
    if end > start:
      discard syscall3(SYS_write, STDOUT, cast[int32](buffer + start), end - start)

    # Write newline
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

    j = j + 1

proc main() =
  var argc: int32 = get_argc()

  # Initialize random seed
  init_rand()

  var fd: int32

  if argc < 2:
    # Read from stdin
    fd = STDIN
  else:
    # Open file
    var filename: ptr uint8 = get_argv(1)
    fd = syscall2(SYS_open, cast[int32](filename), O_RDONLY)
    if fd < 0:
      print_err(cast[ptr uint8]("shuf: cannot open file\n"), 23)
      discard syscall1(SYS_exit, 1)

  # Read and shuffle
  read_and_shuffle(fd)

  # Close file if not stdin
  if fd != STDIN:
    discard syscall1(SYS_close, fd)

  discard syscall1(SYS_exit, 0)
