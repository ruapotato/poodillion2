# PoodillionOS

**A Real Operating System - From Bootloader to Kernel**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

---

## 🎉 Current Status: **MINI-NIM KERNEL BOOTS!** 🎉

```
========================================
  PoodillionOS Mini-Nim Kernel Booted!
========================================

Status: GRUB multiboot successful!
Bootloader: GRUB handled protected mode
Kernel: Compiled from Mini-Nim source!
Size: 9052 bytes (720 byte .o + multiboot)

VGA output: "MINI" in green text
```

**What Works:**
- ✅ **C Kernel** boots successfully via GRUB
- ✅ **Mini-Nim Kernel** compiles and boots via GRUB
- ✅ **Mini-Nim Compiler** generates x86 assembly in kernel mode
- ✅ **Serial Port Output** works in both C and Mini-Nim kernels
- ✅ **VGA Text Mode** for visual output
- ✅ **Protected Mode** transition handled by GRUB
- ✅ **QEMU Testing** with serial and VGA output

**What Doesn't Work (Yet):**
- ❌ **Custom 2-Stage Bootloader** (hangs during protected mode transition)
  - See `GRUB_SETUP.md` for details on the workaround

---

## 🚀 Quick Start

### Boot the Mini-Nim Kernel (NEW!)

```bash
# Build and boot Mini-Nim kernel with serial output
make run-grub-mininim

# Output:
# ========================================
#   Mini-Nim Kernel Booted!
# ========================================
#
# Compiled from Mini-Nim source!
# Compiler: Mini-Nim -> x86 assembly
# Bootloader: GRUB multiboot
#
# Calling Mini-Nim kernel_main()...
```

### Boot the C Kernel

```bash
# Boot C kernel with GRUB (shows output in terminal)
make run-grub

# Ctrl-C to exit QEMU
```

You'll see the kernel boot message and status via serial output!

### Alternative: Use GUI Window

```bash
# Build GRUB ISO
make grub

# Boot with GUI (see VGA text output)
make run-grub-iso
```

---

## 🛠️ Building

```bash
# Check required tools
make check-tools

# Build and boot Mini-Nim kernel
make run-grub-mininim

# Build and boot C kernel
make run-grub

# Or build without running
make grub-mininim  # Mini-Nim kernel
make grub          # C kernel

# Clean everything
make clean
```

---

## 📁 Project Structure

```
poodillion2/
├── boot/                      # Bootloader code
│   ├── stage1.asm            # MBR bootloader (512 bytes)
│   ├── stage2.asm            # Second stage (has pmode bug)
│   ├── multiboot.asm         # GRUB multiboot header ✅
│   ├── boot.asm              # Original kernel entry
│   ├── linker.ld             # Custom bootloader linker
│   └── linker_grub.ld        # GRUB multiboot linker ✅
├── kernel/
│   ├── kernel.c              # Working C kernel ✅
│   └── kernel.nim            # Mini-Nim kernel source
├── compiler/                  # Mini-Nim Compiler
│   ├── mininim.py            # Compiler driver
│   ├── lexer.py              # Tokenizer
│   ├── parser.py             # Parser
│   └── codegen_x86.py        # x86 code generator
├── build/
│   ├── poodillion.img        # Custom bootloader disk (buggy)
│   ├── poodillion_grub.iso   # GRUB ISO (working) ✅
│   └── iso/boot/kernel.elf   # Multiboot kernel ✅
├── GRUB_SETUP.md             # Bootloader issue documentation
└── Makefile
```

---

## 🔧 Current Kernel Features

### Mini-Nim Kernel (kernel.nim) ✨ NEW!

```nim
# Simplest possible kernel - direct memory writes
proc main() =
  # Write "MINI" to VGA memory at 0xB8000
  cast[ptr uint8](0xB8000)[0] = cast[uint8]('M')
  cast[ptr uint8](0xB8001)[0] = cast[uint8](0x02)  # Green

  cast[ptr uint8](0xB8002)[0] = cast[uint8]('I')
  cast[ptr uint8](0xB8003)[0] = cast[uint8](0x02)
  # ... and so on
```

**Features:**
- Written in Mini-Nim (custom Nim-like language)
- Compiles to x86 assembly via custom compiler
- VGA text mode output (green text)
- Boots via GRUB multiboot
- Only 720 bytes of compiled code!

**Compiler Pipeline:**
```
kernel.nim → Mini-Nim Compiler → kernel.asm → NASM → kernel.o
kernel.o + multiboot.o → LD → kernel.elf → QEMU
```

### C Kernel (kernel.c)

```c
void kernel_main(void) {
    serial_init();                    // Initialize COM1 serial port
    serial_print("Kernel Booted!\n"); // Output to serial console

    // Write to VGA memory
    uint16_t* vga = (uint16_t*)0xB8000;
    const char* msg = "BOOTLOADER WORKS! Mini-Nim coming soon...";
    // ... display message in green
}
```

**Features:**
- Serial port output (COM1, 38400 baud)
- VGA text mode (80x25, color)
- Both serial and VGA output work simultaneously
- Visible via `-serial stdio` in QEMU

---

## 🎯 Boot Methods Comparison

| Method | Status | Output | Use Case |
|--------|--------|--------|----------|
| **Custom Bootloader** | ❌ Broken | Hangs | Not usable yet |
| **GRUB (Direct)** | ✅ Working | Serial + VGA | Development (recommended) |
| **GRUB (ISO)** | ✅ Working | GUI/VGA | Testing/Distribution |

### Why GRUB?

The custom 2-stage bootloader has a bug in the protected mode transition (boot/stage2.asm:89). GRUB handles this complex low-level stuff for us, so we can focus on kernel development.

See `GRUB_SETUP.md` for technical details about the bootloader issue.

---

## 📊 Memory Map

```
Physical Memory:
0x00000000 - 0x000003FF   BIOS interrupt vectors
0x00000400 - 0x000004FF   BIOS data area
0x00007C00 - 0x00007DFF   Bootloader stage 1 (if used)
0x00007E00 - 0x00009FFF   Bootloader stage 2 (if used)
0x000B8000 - 0x000B8F9F   VGA text mode buffer (80x25)
0x00100000 - 0x001FFFFF   Kernel code and data (loaded by GRUB)
```

---

## 🚧 Development Roadmap

### ✅ Phase 1: Boot Successfully (COMPLETE!)
- [x] Get kernel to boot and display output
- [x] GRUB multiboot setup
- [x] Serial port output for debugging
- [x] VGA text mode output

### ✅ Phase 2: Mini-Nim Integration (COMPLETE!)
- [x] Update Mini-Nim compiler for kernel mode
- [x] Compile kernel from Mini-Nim source
- [x] Test Mini-Nim kernel boots like C kernel
- [x] Verify output matches

### 📋 Phase 3: Interactive Features (NEXT)
- [ ] Keyboard input driver
- [ ] Simple command parser
- [ ] Memory management
- [ ] Basic shell/REPL

### 🎯 Phase 4: Advanced OS Features
- [ ] Process/task management
- [ ] Filesystem support
- [ ] User programs
- [ ] Self-hosting compiler

### 🔧 Phase 5: Fix Custom Bootloader (OPTIONAL)
- [ ] Debug protected mode transition
- [ ] Compare with working bootloader examples
- [ ] Fix GDT/IDT setup
- [ ] Test on real hardware

---

## 🔬 Technical Details

### Boot Process (GRUB Method)

1. **BIOS/UEFI** loads GRUB from disk/ISO
2. **GRUB** reads `grub.cfg`, finds kernel
3. **GRUB** loads kernel.elf to 0x100000 (1MB)
4. **GRUB** switches to protected mode, sets up basic GDT
5. **GRUB** jumps to kernel entry with:
   - EAX = 0x2BADB002 (multiboot magic)
   - EBX = multiboot info structure address
6. **Kernel** `_start` sets up stack
7. **Kernel** calls `kernel_main()`
8. **Kernel** initializes serial + VGA
9. **Kernel** displays boot message
10. **Kernel** halts (infinite loop)

### Compilation Pipeline

```
kernel.c → GCC (-m32 -ffreestanding) → kernel.o
multiboot.asm → NASM (-f elf32) → multiboot.o
kernel.o + multiboot.o → LD (custom linker script) → kernel.elf
kernel.elf → GRUB ISO / direct boot
```

---

## 🤝 Contributing

Want to help build a real OS? Here are some tasks:

**Easy:**
- Test on different QEMU versions
- Improve documentation
- Add more serial output messages

**Medium:**
- Implement keyboard driver
- Add basic memory management
- Create simple shell

**Hard:**
- Fix custom bootloader protected mode bug
- Port Mini-Nim compiler to kernel
- Implement multitasking

See issues on GitHub for specific tasks.

---

## 📚 Resources & References

### Our Documentation
- `GRUB_SETUP.md` - Bootloader issue details and GRUB setup
- `Makefile` - See `make help` for all targets

### External Resources
- [OSDev Wiki](https://wiki.osdev.org/) - OS development reference
- [GRUB Multiboot](https://www.gnu.org/software/grub/manual/multiboot/) - Multiboot specification
- [x86 Assembly](https://www.nasm.us/doc/) - NASM documentation

---

## 🎮 About Poodillion

Originally a Python-based Unix hacking game simulating a complete 1990s Unix system. Now we're building it for real!

**Evolution:**
1. **Poodillion 1** - Terminal hacking game concept
2. **Poodillion 2** - Full Unix simulator in Python (archived in `game/`)
3. **PoodillionOS** - Real operating system (current)

---

## 📜 License

**GPL-3.0** - See [LICENSE](LICENSE)

All code is free software. Hack away!

---

## 🌟 Status Summary

```
Project: PoodillionOS
Status:  MINI-NIM KERNEL BOOTING! ✅
Method:  GRUB Multiboot
Kernel:  C + Mini-Nim (both working!)
Compiler: Custom Mini-Nim to x86
Output:  Serial port + VGA
Next:    Keyboard input & interactive features
```

**Run the Mini-Nim kernel right now:**
```bash
make run-grub-mininim
```

**Or run the C kernel:**
```bash
make run-grub
```

Press Ctrl-C to exit. Let's build an OS! 🚀

---

**Built with ❤️ and x86 assembly**

*PoodillionOS - Real Hardware, Real OS, Real Learning*
