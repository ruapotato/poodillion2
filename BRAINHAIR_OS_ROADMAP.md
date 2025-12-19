# Brainhair OS: From Virtual to Real

## Vision
Transform Brainhair 2 from a Python-based Unix simulator into a real, bootable operating system with PooScript as a compiled systems language.

---

## Current Architecture (Python Simulation)

```
┌─────────────────────────────────────┐
│         Python Runtime              │
├─────────────────────────────────────┤
│  PooScript Interpreter              │
├─────────────────────────────────────┤
│  VFS │ Processes │ TTY │ Network   │
├─────────────────────────────────────┤
│  UnixSystem (Virtual Kernel)        │
└─────────────────────────────────────┘
```

**Problem:** Runs on top of host OS, interpreted, slow, not real hardware

---

## Target Architecture (Native OS)

```
┌─────────────────────────────────────┐
│       Hardware (x86_64/ARM)         │
├─────────────────────────────────────┤
│  Brainhair Microkernel (C/Rust)   │
│  - Memory management                │
│  - Process scheduler                │
│  - Hardware abstraction             │
├─────────────────────────────────────┤
│  System Services (Compiled PooScript)│
│  - VFS │ TTY │ Network │ Shell     │
├─────────────────────────────────────┤
│  User Programs (Compiled PooScript) │
│  - ls, ps, cat, ssh, etc.          │
└─────────────────────────────────────┘
```

---

## Phase 1: PooScript Compiler (poocc)

### Goal
Compile PooScript to native code via C, Rust, or Nim backend.

### Language Choice Analysis

| Language | Pros | Cons |
|----------|------|------|
| **C** | Direct, no runtime, kernel-friendly | Manual memory, unsafe |
| **Rust** | Memory safe, modern, no GC | Steep learning curve |
| **Nim** | Python-like syntax, compiles to C | Smaller ecosystem |
| **Zig** | Modern C alternative, simple | Young language |

**Recommendation:** Start with **C** for kernel, **Rust** for userspace.

### PooScript → C Compilation Strategy

**Example PooScript:**
```bash
#!/bin/pooscript
echo "Hello from PooScript"
ls -la /tmp
```

**Compiled to C:**
```c
#include "poo_runtime.h"

int main(int argc, char** argv) {
    poo_echo("Hello from PooScript");

    char* ls_args[] = {"ls", "-la", "/tmp", NULL};
    poo_exec("/bin/ls", ls_args);

    return 0;
}
```

### Compiler Architecture

```
PooScript Source
      ↓
   Lexer (tokenize)
      ↓
   Parser (AST)
      ↓
   Semantic Analysis
      ↓
   IR (Intermediate Representation)
      ↓
   Code Generator
      ↓
   C/Rust/Nim Output
      ↓
   gcc/rustc/nim compile
      ↓
   Native Binary
```

### Runtime Library (libpoo)

Core functions PooScript needs:
```c
// libpoo.h - PooScript runtime
#include <stdint.h>

// System calls
int poo_open(const char* path, int flags);
int poo_read(int fd, void* buf, size_t count);
int poo_write(int fd, const void* buf, size_t count);
int poo_close(int fd);

// Process management
int poo_fork(void);
int poo_exec(const char* path, char** argv);
void poo_exit(int status);

// Built-ins
void poo_echo(const char* str);
void poo_cd(const char* path);
char* poo_pwd(void);

// String operations
char* poo_concat(const char* a, const char* b);
int poo_strcmp(const char* a, const char* b);
```

---

## Phase 2: Kernel Rewrite

### Minimal Kernel Requirements

**bootloader.asm** (x86_64):
```asm
; GRUB multiboot2 bootloader
section .multiboot
    dd 0xe85250d6  ; magic
    dd 0           ; architecture
    dd header_end - header_start
    ; ... checksum
```

**kernel.c** (Main kernel):
```c
#include <stdint.h>

// Memory management
void* kmalloc(size_t size);
void kfree(void* ptr);

// Process scheduler
struct process {
    uint64_t pid;
    uint64_t* page_table;
    void* stack;
    void (*entry)(void);
};

void schedule(void);

// VFS interface
struct vfs_node {
    char name[256];
    uint32_t inode;
    uint32_t mode;
    uint64_t size;
    // ... operations
};

// Entry point
void kernel_main(void) {
    // Initialize memory
    mem_init();

    // Initialize VFS
    vfs_init();

    // Mount root filesystem
    mount_rootfs();

    // Start init process
    spawn_init();

    // Enter scheduler
    schedule();
}
```

### Components to Rewrite

1. **Memory Manager** (C/Rust)
   - Page allocation
   - Virtual memory
   - Heap allocator

2. **Process Scheduler** (C/Rust)
   - Round-robin or CFS
   - Context switching
   - Signals

3. **VFS** (Compiled PooScript?)
   - Inode management
   - File operations
   - Device files

4. **TTY Driver** (C/Rust)
   - Serial console
   - VGA text mode
   - Line discipline

5. **Network Stack** (Compiled PooScript?)
   - Ethernet driver
   - TCP/IP
   - Sockets

---

## Phase 3: Bootable Image

### Build System

**Makefile:**
```makefile
CC = gcc
CFLAGS = -m64 -nostdlib -nostdinc -fno-builtin -fno-stack-protector

all: brainhair.iso

kernel.bin: kernel.o boot.o
	ld -T linker.ld -o kernel.bin kernel.o boot.o

brainhair.iso: kernel.bin
	mkdir -p iso/boot/grub
	cp kernel.bin iso/boot/
	cp grub.cfg iso/boot/grub/
	grub-mkrescue -o brainhair.iso iso/

run: brainhair.iso
	qemu-system-x86_64 -cdrom brainhair.iso
```

### Test in VM
```bash
# Build OS
make

# Run in QEMU
make run

# Or VirtualBox
VBoxManage createvm --name BrainhairOS --register
VBoxManage modifyvm BrainhairOS --memory 512 --boot1 disk
VBoxManage storagectl BrainhairOS --name IDE --add ide
VBoxManage storageattach BrainhairOS --storagectl IDE --port 0 --device 0 --type dvddrive --medium brainhair.iso
```

---

## Phase 4: Hardware Support

### Device Drivers Needed

- **VGA Text Mode**: 80x25 console
- **PS/2 Keyboard**: Input
- **Serial Port**: Debug output
- **ATA/IDE**: Hard drive
- **RTL8139**: Network card (simple to implement)
- **Timer (PIT/APIC)**: Scheduling

### Filesystem

**Option 1:** ext2 (well-documented, simple)
**Option 2:** Custom PooFS (based on current VFS design)

```c
struct poo_inode {
    uint32_t ino;
    uint32_t mode;      // permissions
    uint32_t uid;
    uint32_t gid;
    uint64_t size;
    uint64_t blocks[12]; // direct blocks
    uint64_t indirect;   // indirect block
};
```

---

## Phase 5: Userspace

### Init System (PooScript)
```bash
#!/bin/pooscript
# /sbin/init

echo "BrainhairOS booting..."

# Mount filesystems
mount /dev/hda1 /
mount /proc /proc -t procfs
mount /sys /sys -t sysfs

# Start network daemon
/sbin/netd &

# Start TTYs
for i in 1 2 3 4 5 6; do
    /sbin/getty /dev/tty$i &
done

# Wait forever
while true; do
    sleep 1
done
```

### Core Utilities (Compiled PooScript)
All your existing commands become native:
- `/bin/ls` → `ls.poo` → compiled to native binary
- `/bin/ps` → `ps.poo` → compiled to native binary
- `/bin/cat` → `cat.poo` → compiled to native binary

---

## Timeline Estimate

| Phase | Duration | Difficulty |
|-------|----------|-----------|
| **Phase 1: poocc compiler** | 2-3 months | Medium |
| **Phase 2: Kernel rewrite** | 6-12 months | Hard |
| **Phase 3: Bootable image** | 1 month | Medium |
| **Phase 4: Hardware drivers** | 3-6 months | Hard |
| **Phase 5: Userspace** | 2-3 months | Easy |
| **Total** | 14-25 months | |

---

## Minimal Viable OS (MVO)

Start simple - what's the smallest bootable BrainhairOS?

```
1. Bootloader (GRUB)
2. Kernel (1000 lines of C)
   - Memory allocation
   - Process spawn
   - System calls
3. Single PooScript binary (/sbin/init)
4. Serial console output
```

**Result:** Boots, prints "BrainhairOS", runs one PooScript program.

---

## Why This Is Awesome

1. **Educational**: Learn OS development from a working design
2. **Unique**: PooScript as a systems language is novel
3. **Fun**: Keep the 1990s aesthetic, make it retro
4. **Practical**: Could run on real hardware (old laptops, Raspberry Pi)
5. **Hackable**: Perfect for CTF/hacking challenges on bare metal

---

## Similar Projects for Inspiration

- **SerenityOS**: https://serenityos.org/
- **ToaruOS**: https://toaruos.org/
- **Kolibri OS**: https://kolibrios.org/
- **MenuetOS**: http://menuetos.net/
- **TempleOS**: https://templeos.org/ (RIP Terry)

---

## Next Steps

1. **Start poocc**: Build a basic PooScript → C compiler
2. **Prototype kernel**: Get "Hello World" booting in QEMU
3. **Port VFS**: Rewrite core/vfs.py in C
4. **One binary**: Compile one PooScript program and run it

**First Goal:** Boot BrainhairOS in QEMU and run compiled `/bin/ls`

---

## Resources

### OS Development
- **OSDev Wiki**: https://wiki.osdev.org/
- **Writing an OS in Rust**: https://os.phil-opp.com/
- **The Little OS Book**: https://littleosbook.github.io/

### Compiler Design
- **Crafting Interpreters**: https://craftinginterpreters.com/
- **LLVM Tutorial**: https://llvm.org/docs/tutorial/
- **Compilers: Principles, Techniques, and Tools** (Dragon Book)

### PooScript Compilation
Current PooScript interpreter: `core/pooscript.py`
- Already has parsing
- Already has execution model
- Just need code generation backend

---

**This is absolutely doable.** The architecture is already designed. You just need to:
1. Compile PooScript instead of interpreting it
2. Replace Python runtime with native kernel
3. Boot on real hardware

The game becomes an OS. The OS is the game. 🎮🔥
