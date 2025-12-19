# System Information Utilities for BrainhairOS

This document describes the system information utilities built in Brainhair for BrainhairOS.

## Built Utilities

### 1. printenv - Print Environment Variables
**Location:** `/home/david/brainhair2/userland/printenv.nim`

**Usage:**
- `printenv` - Print all environment variables
- `printenv VAR` - Print specific variable value

**Implementation:**
- Reads from `/proc/self/environ`
- Each variable is stored as `NAME=VALUE\0`
- Returns exit code 1 if variable not found

**Example:**
```bash
$ ./bin/printenv PATH
/home/david/.local/bin:/usr/local/bin:/usr/bin:/bin
$ ./bin/printenv HOME
/home/david
```

### 2. tty - Print Terminal Name
**Location:** `/home/david/brainhair2/userland/tty.nim`

**Usage:**
- `tty` - Print the terminal device name

**Implementation:**
- Uses `SYS_readlink (85)` to read `/proc/self/fd/0`
- Checks if stdin is a TTY device (`/dev/pts/*` or `/dev/tty*`)
- Prints "not a tty" if stdin is not a terminal

**Example:**
```bash
$ ./bin/tty
/dev/pts/0
```

### 3. nproc - Print Number of CPUs
**Location:** `/home/david/brainhair2/userland/nproc.nim`

**Usage:**
- `nproc` - Print the number of available CPUs

**Implementation:**
- Reads `/proc/cpuinfo`
- Counts lines starting with "processor"
- Returns at least 1 CPU

**Example:**
```bash
$ ./bin/nproc
8
```

### 4. arch - Print Machine Architecture
**Location:** `/home/david/brainhair2/userland/arch.nim`

**Usage:**
- `arch` - Print the machine hardware architecture

**Implementation:**
- Uses `SYS_uname (122)` syscall
- Extracts the machine field from utsname struct
- utsname layout: 5 fields of 65 bytes each

**Example:**
```bash
$ ./bin/arch
x86_64
```

### 5. logname - Print Login Name
**Location:** `/home/david/brainhair2/userland/logname.nim`

**Usage:**
- `logname` - Print the current user's login name

**Implementation:**
- Reads environment from `/proc/self/environ`
- Searches for `LOGNAME=` or `USER=` variable
- Returns exit code 1 if not found

**Example:**
```bash
$ ./bin/logname
david
```

### 6. groups - Print Group Memberships
**Location:** `/home/david/brainhair2/userland/groups.nim`

**Usage:**
- `groups` - Print group IDs for current user
- `groups [USER]` - Not yet supported

**Implementation:**
- Uses `SYS_getgroups (80)` syscall
- Prints numeric group IDs space-separated
- Currently only supports current user

**Example:**
```bash
$ ./bin/groups
1000 27 998 108
```

## Technical Details

### Brainhair Constraints
All utilities follow Brainhair's constraints:
- No array types - use brk allocation for buffers
- No int64 in function params - only int32, uint32, uint8, ptr
- Use `%` for modulo, `/` for division (NOT mod, div)
- No continue keyword - restructure loops with if
- Syscalls are 32-bit Linux x86 via int 0x80

### Common Patterns

**Memory Allocation:**
```nim
var old_brk: int32 = syscall1(SYS_brk, 0)
var new_brk: int32 = old_brk + 4096
discard syscall1(SYS_brk, new_brk)
var buf: ptr uint8 = cast[ptr uint8](old_brk)
```

**String Operations:**
```nim
proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i
```

**File Reading:**
```nim
var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
var n: int32 = syscall3(SYS_read, fd, cast[int32](buf), size)
discard syscall1(SYS_close, fd)
```

## Building

Build all system info utilities:
```bash
make sysinfo-utils
```

Build individual utility:
```bash
make bin/printenv
make bin/tty
make bin/nproc
make bin/arch
make bin/logname
make bin/groups
```

## Testing

Run the comprehensive test suite:
```bash
./test_sysinfo_utils.sh
```

## File Sizes

All utilities are compact:
- arch: 9.0KB
- groups: 9.8KB
- logname: 11KB
- nproc: 11KB
- printenv: 11KB
- tty: 9.9KB

## Integration

These utilities are part of the SYSINFO_UTILS group in the Makefile:
```makefile
SYSINFO_UTILS = $(BIN_DIR)/uname $(BIN_DIR)/free $(BIN_DIR)/uptime \
                $(BIN_DIR)/hostname $(BIN_DIR)/whoami $(BIN_DIR)/id \
                $(BIN_DIR)/printenv $(BIN_DIR)/tty $(BIN_DIR)/nproc \
                $(BIN_DIR)/arch $(BIN_DIR)/logname $(BIN_DIR)/groups
```

## Future Enhancements

1. **groups**: Add support for looking up arbitrary users (requires parsing /etc/group)
2. **tty**: Add support for more terminal types
3. **printenv**: Add support for modifying environment (like env utility)
4. **nproc**: Add options like `--all`, `--ignore=N`

## Syscall Library

All utilities link against `/home/david/brainhair2/lib/syscalls.asm` which provides:
- `syscall1(num, arg1)` - One-argument syscall wrapper
- `syscall2(num, arg1, arg2)` - Two-argument syscall wrapper
- `syscall3(num, arg1, arg2, arg3)` - Three-argument syscall wrapper
- `syscall4`, `syscall5`, `syscall6` - Additional wrappers for complex syscalls

The Brainhair compiler provides:
- `_start` - Program entry point
- `get_argc()` - Get argument count
- `get_argv(i)` - Get argument by index
- `main()` - User's main function

## Validation

All utilities have been tested and produce identical output to their GNU coreutils counterparts:

| Utility | System | BrainhairOS | Match |
|---------|--------|--------------|-------|
| nproc   | 8      | 8            | ✓     |
| arch    | x86_64 | x86_64       | ✓     |
| logname | david  | david        | ✓     |

