# Process Management Utilities

This document describes the process management utilities implemented for BrainhairOS.

## Overview

Six process management utilities have been implemented in Brainhair:

1. **kill** - Send signals to processes
2. **pidof** - Find PIDs by process name
3. **sleep** - Sleep for N seconds
4. **nohup** - Run commands immune to hangups
5. **nice** - Run commands with modified priority
6. **killall** - Kill all processes by name

## Implementation Details

### 1. kill - Send Signal to Process

**File:** `/home/david/brainhair2/userland/kill.nim`

**Usage:** `kill [-SIGNAL] PID`

**Syscalls Used:**
- `SYS_kill` (37) - Send signal to process

**Features:**
- Sends SIGTERM (15) by default
- Supports SIGKILL (9) and SIGTERM (15)
- Currently demonstrates usage pattern (needs argc/argv for full functionality)

**Example:**
```bash
./bin/kill        # Shows usage
./bin/kill 1234   # Would send SIGTERM to PID 1234
./bin/kill -9 1234 # Would send SIGKILL to PID 1234
```

### 2. pidof - Find PID by Process Name

**File:** `/home/david/brainhair2/userland/pidof.nim`

**Usage:** `pidof processname`

**Syscalls Used:**
- `SYS_open` (5) - Open /proc directory and /proc/PID/comm files
- `SYS_read` (3) - Read process names from comm files
- `SYS_close` (6) - Close file descriptors
- `SYS_getdents64` (220) - List /proc directory entries
- `SYS_brk` (45) - Allocate memory

**Features:**
- Scans /proc filesystem
- Reads /proc/PID/comm files
- Matches process names
- Prints all matching PIDs
- Currently hardcoded to search for "init" (needs argc/argv for arguments)

**Process Discovery Algorithm:**
1. Open /proc directory
2. Iterate through entries using getdents64
3. Filter numeric directories (PIDs)
4. Read /proc/PID/comm for each PID
5. Compare comm with search name
6. Output matching PIDs

### 3. sleep - Sleep for N Seconds

**File:** `/home/david/brainhair2/userland/sleep.nim`

**Usage:** `sleep SECONDS`

**Syscalls Used:**
- `SYS_nanosleep` (162) - Sleep for specified time
- `SYS_brk` (45) - Allocate memory for timespec structure

**Features:**
- Accepts seconds as argument via argc/argv (WORKING!)
- Uses nanosleep syscall for accurate timing
- Allocates timespec structure: `{tv_sec, tv_nsec}`

**Example:**
```bash
./bin/sleep 5   # Sleeps for 5 seconds
time ./bin/sleep 1  # Verify timing accuracy
```

### 4. nohup - Run Command Immune to Hangups

**File:** `/home/david/brainhair2/userland/nohup.nim`

**Usage:** `nohup COMMAND [ARGS...]`

**Syscalls Used:**
- `SYS_open` (5) - Open nohup.out file
- `SYS_fork` (2) - Create child process
- `SYS_dup2` (63) - Redirect stdout/stderr
- `SYS_close` (6) - Close file descriptors
- `SYS_execve` (11) - Execute command (placeholder)

**Features:**
- Creates nohup.out file (O_WRONLY | O_CREAT | O_APPEND)
- Forks child process
- Redirects stdout and stderr to nohup.out
- Parent exits immediately
- Child would execve the command (needs full implementation)

**File Flags:**
- O_WRONLY (1) - Write-only
- O_CREAT (64) - Create if doesn't exist
- O_APPEND (1024) - Append mode

### 5. nice - Run Command with Modified Priority

**File:** `/home/david/brainhair2/userland/nice.nim`

**Usage:** `nice [-n PRIORITY] COMMAND [ARGS...]`

**Syscalls Used:**
- `SYS_nice` (34) - Adjust process priority
- `SYS_getpriority` (96) - Get current priority
- `SYS_setpriority` (97) - Set priority (alternative)
- `SYS_fork` (2) - Create child process
- `SYS_execve` (11) - Execute command (placeholder)

**Features:**
- Default increment: +10
- Shows current and new priority
- Forks child with modified priority
- Priority range: -20 (highest) to 19 (lowest)

**Example:**
```bash
./bin/nice          # Run with +10 priority
./bin/nice -n 15    # Would run with +15 priority
```

### 6. killall - Kill All Processes by Name

**File:** `/home/david/brainhair2/userland/killall.nim`

**Usage:** `killall [-SIGNAL] processname`

**Syscalls Used:**
- `SYS_open` (5) - Open /proc directory and comm files
- `SYS_read` (3) - Read process names
- `SYS_close` (6) - Close file descriptors
- `SYS_getdents64` (220) - List directory entries
- `SYS_kill` (37) - Send signal to each process
- `SYS_brk` (45) - Allocate memory

**Features:**
- Combines pidof + kill functionality
- Finds all processes matching name
- Sends signal to each (default SIGTERM)
- Reports success/failure for each PID
- Currently hardcoded to search for "sleep" processes

**Algorithm:**
1. Scan /proc for all PIDs
2. Read /proc/PID/comm for each
3. Collect matching PIDs in array
4. Iterate through array and kill each
5. Report results

**Example Output:**
```
killall: Searching for process: sleep
killall: Killing 1 process(es)...
Killed PID 122657
killall: Successfully killed 1 process(es)
```

## Building

Each utility can be built individually:

```bash
make bin/kill
make bin/pidof
make bin/sleep
make bin/nohup
make bin/nice
make bin/killall
```

## Testing

Run the comprehensive test suite:

```bash
./test_process_utils.sh
```

This tests all utilities and provides output showing their functionality.

## File Sizes

```
kill    - 9.9K
pidof   - 11K
sleep   - 9.3K
nohup   - 9.8K
nice    - 9.9K
killall - 12K
```

## Architecture Notes

### /proc Filesystem Parsing

The utilities use the following pattern for /proc parsing (based on `ps.nim`):

1. **Open /proc directory** with O_DIRECTORY flag
2. **Use getdents64** to iterate directory entries
3. **Parse dirent64 structure:**
   - reclen at offset +16 (uint16)
   - d_name at offset +19 (null-terminated string)
4. **Filter numeric entries** (PIDs only)
5. **Open /proc/PID/comm** for process name
6. **Read and parse** process information

### Syscall Interface

All utilities use the assembly syscall wrappers:
- `syscall1(num, arg1)` - For single-argument syscalls
- `syscall2(num, arg1, arg2)` - For two-argument syscalls
- `syscall3(num, arg1, arg2, arg3)` - For three-argument syscalls

Defined in `/home/david/brainhair2/lib/syscalls.asm`

### Memory Management

All utilities use `SYS_brk` (45) for memory allocation:
```nim
var old_brk: int32 = syscall1(SYS_brk, 0)
var new_brk: int32 = old_brk + size
discard syscall1(SYS_brk, new_brk)
var buffer: ptr uint8 = cast[ptr uint8](old_brk)
```

## Limitations and Future Work

1. **Argument Parsing**: Most utilities need full argc/argv support (sleep already has it!)
2. **Error Handling**: Could be more robust with errno checking
3. **Signal Support**: kill/killall could support all signals
4. **execve Implementation**: nohup/nice need full command execution
5. **SIGHUP Handling**: nohup should also ignore SIGHUP signal
6. **Nice Value Parsing**: nice should parse -n PRIORITY argument

## Integration with BrainhairOS

These utilities demonstrate:
- Real /proc filesystem parsing
- Process signal management
- Process priority control
- Background process execution
- System call interface usage

They serve as templates for other process management utilities like:
- `ps` (already implemented)
- `top`
- `renice`
- `pkill`
- `pgrep`

## References

- Linux syscall numbers: `/usr/include/asm/unistd_32.h`
- Signal numbers: SIGTERM=15, SIGKILL=9
- /proc filesystem: `/proc/PID/comm`, `/proc/PID/stat`
- Priority range: -20 to 19 (nice values)
