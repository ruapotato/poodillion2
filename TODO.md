# Poodillion 2 - Realism Improvements TODO

## 🎯 Priority 1: Script Language System

### Design VirtualScript Language
- [ ] Simple Python-like syntax (subset for safety)
- [ ] Variables, conditionals, loops
- [ ] Built-in functions for VFS access
- [ ] No dangerous features (no imports, no exec, no file I/O outside VFS)

### Script Interpreter
- [ ] Parse and execute VirtualScript
- [ ] Provide API: `vfs`, `args`, `stdin`, `stdout`, `stderr`
- [ ] Handle errors gracefully
- [ ] Sandboxed execution

### Integration
- [ ] Check if binary is script (starts with `#!`)
- [ ] Execute scripts through interpreter
- [ ] Fall back to Python command handlers for builtins

## 🔒 Priority 2: Permission Enforcement

### Execute Permissions
- [x] Check if binary exists in PATH (DONE)
- [ ] Enforce +x permission before executing
- [ ] Root can execute anything
- [ ] Non-root needs +x bit

### SUID/SGID Support
- [ ] Detect SUID/SGID bits (already in permissions.py)
- [ ] Spawn process with elevated privileges
- [ ] Classic Unix privilege escalation vulnerabilities!

## 🛠️ Priority 3: Essential Commands

### File Permission Commands
- [ ] `chmod` - change file permissions
  - Basic: `chmod 755 file`
  - Symbolic: `chmod +x file`
  - Recursive: `chmod -R`

- [ ] `chown` - change file ownership
  - Basic: `chown user:group file`
  - Recursive: `chown -R`

### Symlink Support
- [ ] `ln` - create hard and symbolic links
  - Symlink: `ln -s target link`
  - Hard link: `ln target link`
  - VFS already supports symlinks!

### File Operations
- [ ] `cp` - copy files (basic implementation)
- [ ] `mv` - move/rename files (basic implementation)

## 🌐 Priority 4: Standard Unix Environment

### Symlinks
- [ ] `/bin/sh -> /bin/bash`
- [ ] `/usr/bin/python -> /usr/bin/python3`
- [ ] Add more standard symlinks

### Environment Variables
- [ ] `$PATH` support (already exists)
- [ ] `$HOME`, `$USER`, `$SHELL` (already exists)
- [ ] `$PWD` automatic update

### Standard Files
- [ ] `/etc/group` file
- [ ] Update `/etc/passwd` format
- [ ] `/etc/profile`, `/etc/bash_profile`

## 🎮 Priority 5: Game Mechanics

### Rootkit Possibilities
- [ ] Players can edit `/bin/ls` to hide files
- [ ] Players can edit `/bin/ps` to hide processes
- [ ] Players can trojan `/bin/su` or `/bin/ssh`
- [ ] Detection mechanics?

### Script Examples
Create example scripts for players to study:
- [ ] `/bin/ls` - simple directory lister
- [ ] `/bin/cat` - simple file reader
- [ ] `/bin/whoami` - shows current user
- [ ] `/usr/local/bin/backdoor` - example exploit

### Security Challenges
- [ ] SUID binary exploitation
- [ ] PATH injection attacks
- [ ] Symlink race conditions
- [ ] Permission misconfigurations

## 📝 VirtualScript Language Spec (Draft)

```python
#!/usr/bin/virtualscript
# Simple Python-like language for commands

# Built-in functions available:
# - print(text) - write to stdout
# - error(text) - write to stderr
# - exit(code) - exit with code
# - len(list) - get length
# - str(x), int(x) - conversions

# Built-in objects:
# - args - list of command arguments
# - stdin - input text
# - vfs - filesystem access
#   - vfs.list(path) - list directory
#   - vfs.read(path) - read file
#   - vfs.stat(path) - get file info
#   - vfs.exists(path)
# - env - environment variables dict
# - process - current process info
#   - process.uid, process.gid
#   - process.cwd

# Example: simple ls command
if len(args) == 0:
    path = "."
else:
    path = args[0]

entries = vfs.list(path)
for name in entries:
    print(name)
```

## 🐛 Known Issues to Fix
- [ ] `pwd` command returns empty output
- [ ] Need better error messages
- [ ] Tab completion would be cool (future)

## 🚀 Performance Optimizations (Later)
- [ ] Cache path lookups
- [ ] Optimize inode traversal
- [ ] Precompile scripts?

## 📚 Documentation (Future)
- [ ] Write game tutorial
- [ ] Document VirtualScript language
- [ ] Create hacking challenges/scenarios
- [ ] Write README with gameplay examples

---

## Implementation Order
1. ✅ Binary existence checking (DONE)
2. Execute permission enforcement
3. chmod/chown/ln commands
4. VirtualScript interpreter
5. Rewrite binaries as scripts
6. Game testing and polish
