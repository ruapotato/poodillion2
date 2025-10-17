# PoodillionOS

**A Unix-like Operating System with PooScript as a compiled systems language**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

---

## 🚀 Vision

Transform the Poodillion 2 game simulation into a real, bootable operating system running on bare metal hardware.

**Current Status**: 🔨 Active Development
- ✅ PooScript → C compiler working
- ✅ OS architecture designed (from game simulation)
- 🚧 Kernel implementation (next step)
- 📋 Bootloader & drivers (planned)

---

## 🎮 What is Poodillion?

Originally a Python-based Unix hacking game set in December 1990, Poodillion simulated a complete Unix-like OS with networking, processes, filesystems, and a custom scripting language called PooScript.

**Now**: We're compiling that simulation into a real OS!

---

## 📁 Project Structure

```
poodillion2/
├── kernel/          # OS kernel (C/Rust)
├── userspace/       # User programs (compiled PooScript)
│   ├── bin/        # User commands
│   ├── sbin/       # System commands
│   ├── poocc_prototype.py    # PooScript → C compiler
│   └── poo_runtime.c/h       # Runtime library
├── boot/            # Bootloader & GRUB config
├── lib/             # Shared libraries (libc, libpoo)
├── docs/            # Documentation
├── game/            # Original Poodillion 2 game (archived)
└── POODILLION_OS_ROADMAP.md  # Development roadmap

```

---

## 🛠️ Quick Start

### Compile PooScript to Native Code

```bash
# Compile a PooScript program
cd userspace
./poocc_prototype.py hello.poo > hello.c
gcc hello.c poo_runtime.c -o hello
./hello
```

Output:
```
Hello from PoodillionOS!
This is native compiled code
/home/user/poodillion2/userspace
```

### Play the Original Game

```bash
cd game
python3 play.py          # Terminal mode
python3 web_server.py    # Web interface (http://localhost:5000)
```

---

## 🏗️ Development Roadmap

See [POODILLION_OS_ROADMAP.md](POODILLION_OS_ROADMAP.md) for complete plan.

### Phase 1: Compiler ✅ DONE
- [x] PooScript → C transpiler
- [x] Runtime library (poo_runtime.c)
- [x] Proof of concept (17KB native binary, 1ms runtime)

### Phase 2: Kernel (In Progress)
- [ ] Bootloader (GRUB multiboot2)
- [ ] Memory management
- [ ] Process scheduler
- [ ] System calls
- [ ] Device drivers (VGA, keyboard, serial)

### Phase 3: Userspace
- [ ] Port game scripts to compiled binaries
- [ ] /sbin/init (system initialization)
- [ ] Core utilities (ls, ps, cat, etc.)

### Phase 4: Boot & Test
- [ ] Build bootable ISO
- [ ] Run in QEMU
- [ ] Boot on real hardware

---

## 🔧 Building

```bash
# Build everything
make all

# Build kernel only
make kernel

# Build userspace programs
make userspace

# Create bootable ISO
make iso

# Run in QEMU
make run
```

*(Makefile coming soon)*

---

## 📚 Documentation

- [Kernel Architecture](kernel/README.md)
- [PooScript Compiler](userspace/README.md)
- [Boot Process](boot/README.md)
- [Game Documentation](game/README.md)

---

## 🎯 Why This Exists

1. **Educational**: Learn OS development from a working design
2. **Novel**: PooScript as a compiled systems language
3. **Fun**: Keep the 1990s hacking game aesthetic on bare metal
4. **Practical**: Could run on vintage hardware (old laptops, Raspberry Pi)

---

## 🤝 Contributing

We're building a real OS! Contributions welcome.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/kernel-scheduler`)
3. Commit your changes
4. Push and create a Pull Request

See [docs/contributing.md](docs/README.md) for more details.

---

## 📜 License

**GPL-3.0** - See [LICENSE](LICENSE) for details.

All code is free software. You can redistribute and modify it under the terms of the GNU General Public License version 3.

---

## 🌟 Inspiration

- **SerenityOS**: Modern Unix from scratch
- **ToaruOS**: Educational OS with beautiful UI
- **TempleOS**: Unique vision (RIP Terry Davis)
- **Redox**: Unix-like in Rust

---

## 📞 Contact

- Issues: https://github.com/ruapotato/poodillion2/issues
- Discussions: https://github.com/ruapotato/poodillion2/discussions

---

**Status**: 🔥 We're going from virtual to real! The compiler works, now we build the kernel.

Join us in creating a Unix-like OS where the scripting language compiles to native code!
