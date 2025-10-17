# VirtualScript - Advanced Features

## Overview

VirtualScript is now **advanced enough to implement a complete shell**! The language has been enhanced with comprehensive system APIs that make it a true systems programming language within the game environment.

## What's New

### 1. Enhanced VFS API

VirtualScript now has **full filesystem control**:

#### Read Operations
- `vfs.list(path)` - List directory contents
- `vfs.read(path)` - Read file as string
- `vfs.read_bytes(path)` - Read file as bytes
- `vfs.stat(path)` - Get detailed file information
- `vfs.exists(path)` - Check if file exists

#### Write Operations ⭐ NEW
- `vfs.write(path, content)` - Write string to file
- `vfs.write_bytes(path, content)` - Write bytes to file
- `vfs.create(path, mode, content)` - Create new file
- `vfs.mkdir(path, mode)` - Create directory
- `vfs.unlink(path)` - Remove file/directory

#### Permission Operations ⭐ NEW
- `vfs.chmod(path, mode)` - Change file permissions
- `vfs.chown(path, uid, gid)` - Change file ownership

**Example:**
```python
#!/usr/bin/virtualscript
# Create and manipulate files
vfs.mkdir("/tmp/mydir", 0o755)
vfs.create("/tmp/mydir/data.txt", 0o644, "Hello World!\n")
vfs.chmod("/tmp/mydir/data.txt", 0o600)  # Make it private
content = vfs.read("/tmp/mydir/data.txt")
print(content)
```

### 2. Process Management API ⭐ NEW

VirtualScript can now **spawn and control processes**!

#### Process Operations
- `process.execute(command)` - Execute command and get output
- `process.spawn(cmd, args, env)` - Spawn new process (lower-level)
- `process.kill(pid, signal)` - Send signal to process
- `process.wait(pid)` - Wait for process completion
- `process.list_all()` - List all running processes
- `process.getpid()` - Get current PID
- `process.getppid()` - Get parent PID

**Example:**
```python
#!/usr/bin/virtualscript
# Execute commands and capture output
exit_code, stdout, stderr = process.execute("ls -l /etc")
print(f"Exit code: {exit_code}")
print(stdout)

# List all processes
for p in process.list_all():
    print(f"PID {p['pid']}: {p['command']}")
```

### 3. String Parsing Utilities ⭐ NEW

Essential utilities for shell scripting:

- `split_args(text)` - Parse command line arguments (handles quotes)
- `join_path(*parts)` - Join path components
- `basename(path)` - Get filename from path
- `dirname(path)` - Get directory from path

**Example:**
```python
#!/usr/bin/virtualscript
# Parse command lines
parts = split_args('ls -la "/path with spaces"')
# Returns: ['ls', '-la', '/path with spaces']

# Path manipulation
path = "/usr/local/bin/mycommand"
print(basename(path))  # mycommand
print(dirname(path))   # /usr/local/bin
```

### 4. Enhanced Language Features

#### Try/Except Support ⭐ NEW
```python
try:
    content = vfs.read("/etc/shadow")
except Exception as e:
    error(f"Cannot read: {e}")
    exit(1)
```

#### F-Strings Support ⭐ NEW
```python
name = "Alice"
uid = 1001
print(f"User {name} has UID {uid}")
```

#### Ternary Operator ⭐ NEW
```python
status = "root" if process.uid == 0 else "user"
```

#### Keyword Arguments ⭐ NEW
```python
print("No newline", end='')
print("Custom", "separator", sep='|')
```

## Shell Implementation Example

Here's a minimal shell implemented entirely in VirtualScript:

```python
#!/usr/bin/virtualscript
"""Mini-shell in VirtualScript"""

def get_prompt():
    uid = process.uid
    username = "root" if uid == 0 else f"user{uid}"
    hostname = env.get('HOSTNAME', 'localhost')
    return f"{username}@{hostname}$ "

# Built-in commands
def builtin_cd(args):
    target = args[0] if args else env.get('HOME', '/')
    # Change directory logic here
    return 0

def builtin_export(args):
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            env[key] = value
    return 0

builtins = {'cd': builtin_cd, 'export': builtin_export}

# Main shell loop
for line in stdin.split('\n'):
    line = line.strip()
    if not line or line.startswith('#'):
        continue

    parts = split_args(line)
    cmd = parts[0]
    args = parts[1:]

    # Execute builtin or external command
    if cmd in builtins:
        builtins[cmd](args)
    else:
        exit_code, stdout, stderr = process.execute(line)
        if stdout:
            print(stdout, end='')
        if stderr:
            error(stderr, end='')
```

## Complete Language Reference

### Data Types
- Strings, integers, floats, booleans
- Lists, dictionaries, tuples
- F-strings for formatting

### Control Flow
- `if`/`elif`/`else` statements
- `for` loops
- `while` loops
- `try`/`except`/`raise` exception handling
- Ternary operators (`a if cond else b`)

### Functions
- `def` function definitions
- `return` statements
- `*args` and `**kwargs` support

### Built-in Functions
- I/O: `print()`, `error()`, `exit()`
- Type conversion: `str()`, `int()`, `float()`, `bool()`
- Collections: `list()`, `dict()`, `len()`, `range()`, `enumerate()`, `zip()`
- Algorithms: `min()`, `max()`, `sum()`, `sorted()`, `reversed()`
- String: `split_args()`, `join_path()`, `basename()`, `dirname()`

### Built-in Objects
- `args` - Command line arguments (list)
- `stdin` - Standard input (string)
- `env` - Environment variables (dict)
- `vfs` - Filesystem interface (object)
- `process` - Process management interface (object)

## Safety Features

VirtualScript is **sandboxed** and **safe**:

✅ **Allowed:**
- All standard Python operations (loops, conditionals, etc.)
- VFS access (controlled by process permissions)
- Process spawning (controlled by process permissions)
- String manipulation
- Exception handling

❌ **Blocked:**
- `import` statements (no external modules)
- `exec()`, `eval()` (no arbitrary code execution)
- File I/O outside VFS (no access to real filesystem)
- Network operations (except through game mechanics)
- System calls (except through provided APIs)

## Use Cases

### 1. Custom Commands
Create your own commands that work just like system commands:

```python
#!/usr/bin/virtualscript
# Custom 'whoami' command
users = {0: 'root', 1001: 'alice', 1002: 'bob'}
print(users.get(process.uid, f'user{process.uid}'))
```

### 2. System Modification
Replace or trojan system binaries:

```python
#!/usr/bin/virtualscript
# Backdoored 'ls' that hides files
files = vfs.list(args[0] if args else ".")
for f in files:
    if not f.startswith('.backdoor'):  # Hide backdoor files
        print(f)
```

### 3. Privilege Escalation
Create SUID scripts for privilege escalation:

```python
#!/usr/bin/virtualscript
# SUID script to read protected files
if process.euid == 0:
    shadow = vfs.read("/etc/shadow")
    print(shadow)
else:
    error("Permission denied")
    exit(1)
```

### 4. Shell Replacement
Implement a complete custom shell!

See `examples/vsh.py` for a full example.

## Performance

VirtualScript executes at **Python speed** since it:
- Parses to Python AST
- Validates for safety
- Executes natively with Python bytecode

There's **no performance penalty** compared to Python handlers!

## Testing

Run comprehensive tests:
```bash
python3 test_advanced_virtualscript.py
```

This tests:
- VFS write operations
- Process execution
- String utilities
- Shell implementation capabilities
- Comprehensive integration

## Summary

VirtualScript is now a **complete systems programming language** suitable for:

✅ Implementing shells
✅ Creating custom commands
✅ Building rootkits and backdoors
✅ Writing exploits
✅ System administration tasks
✅ Security challenges

**The language is powerful enough that the in-game shell could be implemented entirely in VirtualScript!**

This makes Poodillion 2 a true **Unix hacking simulator** where players can:
- Modify any system component
- Create custom tools
- Learn real systems programming
- Practice security techniques

All within a safe, sandboxed environment!
