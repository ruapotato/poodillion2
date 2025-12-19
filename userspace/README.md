# BrainhairOS Userspace

User programs and utilities compiled from PooScript.

## PooScript Compiler (poocc)

Compiles PooScript source code to native C, then to machine code.

```bash
./poocc_prototype.py hello.poo > hello.c
gcc hello.c poo_runtime.c -o hello
./hello
```

## Directory Structure

- `bin/` - User commands (ls, cat, ps, etc.)
- `sbin/` - System commands (init, netd, etc.)
- `poo_runtime.c/h` - Runtime library for compiled programs
- `poocc_prototype.py` - PooScript → C compiler

## Building Userspace

All PooScript programs in game/scripts/ will be compiled to native binaries here.

```bash
make userspace
```
