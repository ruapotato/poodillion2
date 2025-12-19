# Brainhair 2 - Kernel Architecture Design

## Overview

Brainhair 2 now uses a **true kernel/userland architecture** similar to real Unix systems:

- **Python = Kernel**: Low-level syscalls only
- **PooScript = Unix**: All commands, shell, and userland utilities

This makes the system more realistic, more hackable, and more educational.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                  USER SPACE (PooScript)                  │
│                                                           │
│  /bin/ls  /bin/cat  /bin/ps  /bin/sh  /sbin/init       │
│  All commands, utilities, shell, daemons                 │
│                                                           │
│  Uses: vfs.read(), process.spawn(), kernel.open()       │
└─────────────────────────────────────────────────────────┘
                           │
                    Syscall Interface
                           │
┌─────────────────────────────────────────────────────────┐
│                  KERNEL SPACE (Python)                   │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │     VFS      │  │   Process    │  │   Network    │  │
│  │  Filesystem  │  │  Management  │  │    Stack     │  │
│  │   (Inodes)   │  │  (fork/exec) │  │   (Sockets)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
│  Provides: sys_open(), sys_read(), sys_fork(), ...      │
└─────────────────────────────────────────────────────────┘
```

## Syscall Interface

### New: `core/kernel.py`

The kernel module provides syscalls for userland programs:

```python
from core.kernel import Kernel, Syscall

kernel = Kernel(vfs, process_manager, permissions, network)

# File operations
fd = kernel.sys_open(pid, "/etc/passwd", O_RDONLY)
data = kernel.sys_read(pid, fd, 1024)
kernel.sys_close(pid, fd)

# Process operations
child_pid = kernel.sys_fork(pid)
kernel.sys_exec(pid, "/bin/ls", ["-l"], env)
kernel.sys_kill(pid, target_pid, SIGTERM)

# Directory operations
kernel.sys_mkdir(pid, "/tmp/test", 0o755)
entries = kernel.sys_readdir(pid, "/tmp")
```

### Available to PooScript

PooScript programs can now use the `kernel` object:

```python
#!/usr/bin/pooscript
# Example: using kernel syscalls

# Open file
fd = kernel.open("/etc/passwd", kernel.O_RDONLY)
if fd >= 0:
    data = kernel.read(fd, 1024)
    print(data.decode())
    kernel.close(fd)

# Fork a process
child = kernel.fork()
if child == 0:
    # Child process
    print("I'm the child!")
    kernel.exit(0)
else:
    # Parent process
    print(f"Child PID: {child}")
    kernel.wait(child)
```

## Interface Layers

### 1. Low-Level: `kernel` object (NEW)

Direct syscalls - closest to real Unix:

```python
#!/usr/bin/pooscript
fd = kernel.open("/tmp/test.txt", kernel.O_WRONLY | kernel.O_CREAT, 0o644)
kernel.write(fd, b"Hello, world!\n")
kernel.close(fd)
```

### 2. Mid-Level: `vfs` and `process` objects (EXISTING)

Convenience wrappers - easier to use:

```python
#!/usr/bin/pooscript
vfs.create("/tmp/test.txt", 0o644, "Hello, world!\n")
content = vfs.read("/tmp/test.txt")
print(content)
```

### 3. High-Level: Shell commands (PooScript)

Everything is a PooScript program:

```bash
$ ls /tmp
$ cat /etc/passwd
$ ps aux
```

## What Changed

### Before (Mixed Python/PooScript)

- **Python**: VFS, processes, shell, AND commands (commands/fs.py)
- **PooScript**: Some commands (scripts/bin/*)
- **Problem**: Duplicate implementations, not realistic

### After (Pure Kernel/Userland)

- **Python**: Only kernel (VFS syscalls, process syscalls, network syscalls)
- **PooScript**: EVERYTHING in userland (all commands, shell, init, daemons)
- **Benefits**: Realistic, fully hackable, educational

## Implementation Status

### ✅ Completed

1. **core/kernel.py** - Kernel syscall interface
2. **core/pooscript.py** - KernelInterface exposed to PooScript
3. Syscall functions: open, read, write, close, stat, mkdir, unlink, readdir, chdir, fork, exec, wait, kill

### 🚧 In Progress

4. **core/system.py** - Integrate kernel into system initialization
5. **core/shell.py** - Update to pass kernel to PooScript
6. Remove Python commands (commands/fs.py, commands/proc.py)
7. Create full shell in PooScript (/bin/pooshell)

### 📋 TODO

8. Update all call sites to pass kernel parameter
9. Test commands with kernel syscalls
10. Implement missing syscalls as needed
11. Create example programs using kernel interface

## Usage Examples

### Example 1: Simple cat command using kernel

```python
#!/usr/bin/pooscript
# /bin/cat - read files using kernel syscalls

if len(args) == 0:
    # Read from stdin
    print(stdin)
else:
    for filename in args:
        fd = kernel.open(filename, kernel.O_RDONLY)
        if fd < 0:
            error(f"cat: {filename}: No such file or directory")
            exit(1)

        # Read file in chunks
        while True:
            data = kernel.read(fd, 4096)
            if len(data) == 0:
                break
            print(data.decode(), end='')

        kernel.close(fd)

exit(0)
```

### Example 2: Fork/exec pattern

```python
#!/usr/bin/pooscript
# Spawn a child process

child_pid = kernel.fork()

if child_pid == 0:
    # Child process
    kernel.exec("/bin/ls", ["-l", "/tmp"], env)
    # Never returns if exec succeeds
    error("exec failed!")
    kernel.exit(1)
else:
    # Parent process
    print(f"Waiting for child {child_pid}...")
    pid, exit_code = kernel.wait(child_pid)
    print(f"Child exited with code {exit_code}")
```

### Example 3: Shell implementation

```python
#!/usr/bin/pooscript
# /bin/pooshell - simple shell using kernel

while True:
    # Print prompt
    print(f"{env.get('USER', 'user')}@{env.get('HOSTNAME', 'host')}$ ", end='')

    # Read command
    command = input()
    if not command:
        continue

    # Parse command (simplified)
    parts = split_args(command)
    if not parts:
        continue

    cmd = parts[0]
    cmd_args = parts[1:]

    # Fork and exec
    child = kernel.fork()
    if child == 0:
        # Child: execute command
        kernel.exec(f"/bin/{cmd}", [cmd] + cmd_args, env)
        error(f"pooshell: {cmd}: command not found")
        kernel.exit(127)
    else:
        # Parent: wait for child
        kernel.wait(child)
```

## Benefits of This Architecture

### 1. Educational
Learn how real Unix kernels work:
- File descriptors
- Fork/exec model
- Syscall interface
- Kernel vs userland separation

### 2. Hackable
Everything is modifiable:
- Replace /bin/ls with custom version
- Modify shell behavior
- Hook syscalls
- Inject code at any level

### 3. Realistic
Matches real Unix architecture:
- Kernel provides primitives
- Userland builds on them
- Clear separation of concerns
- Standard Unix conventions

### 4. Secure (in game context)
Proper permission checking:
- Syscalls enforce permissions
- No direct VFS access
- SUID/SGID support
- Realistic privilege escalation

## Migration Path

### Phase 1: Dual Mode (Current)
- Keep both Python and PooScript commands
- Kernel available but optional
- Backwards compatible

### Phase 2: Kernel Required
- All commands use kernel syscalls
- Python commands deprecated
- Shell passes kernel to all programs

### Phase 3: Pure PooScript
- Remove commands/*.py entirely
- Everything in PooScript
- True kernel/userland split

## Future Enhancements

### 1. More Syscalls
- `mmap()` - Memory mapping
- `ioctl()` - Device control
- `socket()` - Network sockets
- `pipe()` - Inter-process communication

### 2. System Calls API
- `strace` command to trace syscalls
- Syscall table inspection
- Performance counters

### 3. Kernel Modules
- Loadable kernel modules
- Device drivers as modules
- Filesystem types as modules

### 4. Advanced Features
- Copy-on-write fork
- Process scheduling
- Memory management
- Signal handling

## Conclusion

This new architecture makes Brainhair 2 a true Unix emulator:

1. **Python is the kernel** - provides low-level syscalls
2. **PooScript is Unix** - implements all userland functionality
3. **Clear separation** - realistic and educational
4. **Fully hackable** - modify any part of the system

Just like real Unix: kernel provides primitives, userland builds an operating system!
