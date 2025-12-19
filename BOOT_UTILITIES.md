# BrainhairOS Boot Utilities

Essential system initialization utilities for a bootable BrainhairOS system.

## Overview

These utilities form the core boot chain for BrainhairOS:

1. **init** - PID 1 system initializer
2. **getty** - TTY management and login spawning
3. **login** - User authentication and shell spawning

## Boot Sequence

```
Kernel starts → init (PID 1) → getty → login → shell
```

### 1. init - System Initializer (PID 1)

The first userspace process started by the kernel.

**Location:** `/home/david/brainhair2/userland/init.nim`

**Responsibilities:**
- Mount essential filesystems:
  - `/proc` (procfs)
  - `/sys` (sysfs)
  - `/dev` (devtmpfs)
- Spawn getty on `/dev/tty1`
- Reap zombie processes (wait loop)
- Respawn getty if it dies

**Syscalls used:**
- `SYS_mount` (21) - Mount filesystems
- `SYS_fork` (2) - Create child processes
- `SYS_execve` (11) - Execute getty
- `SYS_waitpid` (7) - Wait for and reap children
- `SYS_getpid` (20) - Check if PID 1

**Main loop:**
```nim
while true:
  wait for child to exit
  if getty died: respawn getty
```

### 2. getty - Get TTY

Opens a TTY device and spawns login.

**Location:** `/home/david/brainhair2/userland/getty.nim`

**Usage:**
```bash
getty /dev/tty1
```

**Responsibilities:**
- Create new session (setsid)
- Open TTY device
- Make TTY the controlling terminal
- Redirect stdin/stdout/stderr to TTY
- Display login banner
- Execute login

**Syscalls used:**
- `SYS_setsid` (66) - Create new session
- `SYS_open` (5) - Open TTY device
- `SYS_ioctl` (54) - Set controlling TTY (TIOCSCTTY)
- `SYS_dup2` (63) - Redirect file descriptors
- `SYS_execve` (11) - Execute login

### 3. login - User Login

Displays login prompt and spawns shell.

**Location:** `/home/david/brainhair2/userland/login.nim`

**Usage:**
```bash
login
```

**Responsibilities:**
- Display login prompt
- Read username
- Validate user (simplified - accepts any username)
- Change to home directory
- Execute shell (psh)

**Syscalls used:**
- `SYS_read` (3) - Read username
- `SYS_write` (4) - Display prompts
- `SYS_chdir` (12) - Change to home directory
- `SYS_execve` (11) - Execute shell

**Future enhancements:**
- Read `/etc/passwd` for user validation
- `SYS_setuid` (23) - Set user ID
- `SYS_setgid` (46) - Set group ID

## Building

Build all boot utilities:
```bash
make boot-utils
```

This creates:
- `bin/init` (~11 KB)
- `bin/getty` (~10 KB)
- `bin/login` (~10 KB)

## Testing

### Test init (not as PID 1)
```bash
./bin/init
```
**Expected behavior:**
- Attempts to mount filesystems (will fail without root)
- Spawns getty on /dev/tty1
- Enters zombie reaping loop

### Test login
```bash
echo "testuser" | ./bin/login
```
**Expected output:**
```
login: testuser

Welcome to BrainhairOS, testuser!
```

### Test getty
```bash
./bin/getty /dev/pts/0  # Use your current terminal
```
**Expected behavior:**
- Displays banner
- Attempts to exec login

## Integration with Kernel

For a bootable system, the kernel should:

1. Mount root filesystem
2. Execute `/sbin/init` or `/bin/init` as PID 1
3. init takes over and:
   - Mounts /proc, /sys, /dev
   - Spawns getty on console
   - Manages system processes

## Brainhair Constraints

These utilities respect Brainhair constraints:

- **No array types** - Use brk allocation for buffers
- **No int64 in params** - Only int32, uint32, uint8, ptr
- **Use % for modulo, / for division** - Not mod, div
- **No continue keyword** - Restructure loops with if
- **32-bit Linux x86 syscalls** - via int 0x80

## File Sizes

```
-rwxrwxr-x 1 david david 11K Dec 18 09:46 bin/init
-rwxrwxr-x 1 david david 10K Dec 18 09:46 bin/getty
-rwxrwxr-x 1 david david 10K Dec 18 09:46 bin/login
```

Total boot chain: ~31 KB of Brainhair code!

## Dependencies

**Required utilities:**
- `psh` - BrainhairOS shell (spawned by login)

**Required filesystems:**
- `/proc` - Process information
- `/sys` - System information
- `/dev` - Device nodes (TTYs)

## Security Notes

**Current implementation is simplified:**
- No password checking in login
- No user/group permission enforcement
- All logins succeed

**For production:**
- Implement /etc/passwd parsing
- Add password verification
- Use setuid/setgid for privilege separation
- Add PAM support

## Future Enhancements

1. **Signal handling in init**
   - SIGCHLD for child notification
   - SIGTERM/SIGINT for shutdown
   - SIGUSR1 for reload

2. **Runlevels**
   - Single user mode
   - Multi-user mode
   - Graphical mode

3. **Multiple gettys**
   - Spawn on multiple TTYs
   - Virtual console support

4. **System shutdown**
   - Kill all processes
   - Unmount filesystems
   - Sync disks
   - Reboot/halt system

5. **Login improvements**
   - Password authentication
   - /etc/passwd and /etc/shadow support
   - Session management
   - Environment setup

## References

- Linux syscall numbers: `/usr/include/asm/unistd_32.h`
- TTY ioctl commands: `/usr/include/asm-generic/ioctls.h`
- Mount flags: `/usr/include/linux/fs.h`

## License

Part of BrainhairOS - The Future of Computing
