# PoodillionOS

**A Data-Oriented Operating System with Type-Safe Binary Pipelines**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

*Unix Performance + PowerShell Composability + Type Safety = **PoodillionOS***

---

## 🎯 What Makes PoodillionOS Different?

Unlike Unix (text streams) or PowerShell (serialized objects), PoodillionOS uses **binary typed data structures** throughout the entire system.

### The Problem with Text Pipes

```bash
# Unix way - fragile, slow, error-prone
$ ps aux | grep python | awk '{print $2}' | xargs kill
# What if process name has spaces? What if columns shift?
```

### The PowerShell Approach

```powershell
# Better composability, but slow serialization
PS> Get-Process | Where-Object {$_.Name -eq "python"} | Stop-Process
# Nice, but .NET object serialization is expensive
```

### The PoodillionOS Way

```bash
# Type-safe, binary, zero-copy pipelines
$ ps | where .name == "python" | select .pid | kill
# Schema: Process{pid:i32, name:str, mem:u64}
# Data: Binary structs, no parsing, no serialization
```

## 🎨 The Type-Aware Shell

PoodillionOS includes `psh`, a **badass type-aware shell** that automatically detects and beautifully displays structured data!

```bash
$ ./bin/psh

╔════════════════════════════════════════════════╗
║  PoodillionOS Shell - Type-Aware Data Shell   ║
║                                                ║
║  • Type-safe binary pipelines                 ║
║  • Automatic schema detection                 ║
║  • Pretty table formatting                    ║
║                                                ║
║  Try: bin/ps | bin/where | bin/select         ║
╚════════════════════════════════════════════════╝

psh> bin/ps

┌─── Schema ───────────────────────┐
│ Magic:   PSCH                     │
│ Version: 1                        │
│ Fields:  3                        │
│ RecSize: 12 bytes                 │
└──────────────────────────────────┘

┌─── Data (3 records) ───────────────┐
│ [0] 01 00 00 00 00 04 00 00 00 00 00 00  │
│ [1] 64 00 00 00 00 08 00 00 00 00 00 00  │
│ [2] c8 00 00 00 00 10 00 00 00 00 00 00  │
└──────────────────────────────────┘
```

**No manual formatting needed** - the shell *understands* your data!

---

## 🚀 Current Status

### ✅ Working Now

**Userland Utilities** (all in Mini-Nim, no libc):
- **echo** (8.9KB) - Display text output
- **cat** (5.1KB) - Concatenate and display files
- **edit** (11KB) - CLI text editor with ANSI colors! ⭐ NEW
- **true** (4.8KB) - Exit with success code
- **false** (4.8KB) - Exit with failure code

**Type-Aware Shell** ⭐ NEW:
- **psh** (14KB) - PoodillionOS Shell with schema awareness!
  - Automatically detects PSCH format
  - Displays schemas in pretty boxes
  - Formats binary data as hex tables
  - Interactive REPL with psh> prompt

**Data-Oriented Tools** (working binary pipeline!):
- **ps** (8.8KB) - Output binary Process objects with schema
- **inspect** (9.6KB) - View schema and hex dump structured data
- **where** (9.7KB) - Filter structured data streams by predicate
- **count** (9.3KB) - Count records in stream
- **head** (9.1KB) - Take first N records
- **tail** (9.2KB) - Take last N records
- **select** (9.0KB) - Project specific fields

**Shell Features** (psh - 13KB):
- 🎨 Beautiful box-drawing UI
- 🔍 Automatic PSCH format detection
- 📊 Pretty hex table formatting
- ⚡ Zero-copy data display
- 💻 Interactive REPL
- 🚀 Process forking & piping
- 📝 Built-in commands: exit, quit

**Compiler Features**:
- Type-safe Mini-Nim → x86 compiler
- Block-scoped parsing with indentation
- Size-aware loads/stores (byte, word, dword)
- Address-of operator (`addr`) for safe pointer operations
- Dynamic stack allocation
- 45+ Linux syscalls exposed
- Zero dependencies (no libc!)

### 📊 Comparison

| Feature | Unix | PowerShell | **PoodillionOS** |
|---------|------|------------|------------------|
| Pipeline Data | Text | .NET Objects | **Binary Structs** |
| Performance | ⚡ Fast I/O | 🐢 Slow (serialize) | **⚡⚡ Zero-copy** |
| Type Safety | ❌ None | ⚠️ Runtime | **✅ Compile-time** |
| Composability | ⚠️ Text processing | ✅ Object methods | **✅ Type-safe operators** |
| Introspection | ❌ Manual | ✅ Reflection | **✅ Schema inspection** |
| Memory | ✅ Efficient | ❌ GC overhead | **✅ Stack/mmap only** |
| Shell UI | Plain text | Tables | **🎨 Beautiful box-drawing** |
| Auto-formatting | ❌ None | ✅ Format-Table | **✅ Automatic schema display** |

---

## 💡 Core Concept: Everything is Structured Data

### Binary Schema Format

Every command outputs a schema + binary data:

```
Header:
  Magic: "PSCH" (4 bytes)
  Version: 1 (1 byte)
  Field count: N (1 byte)
  Record size: S bytes (2 bytes)

Data:
  Record count: M (4 bytes)
  Records: M × S bytes (binary)
```

### Example: Process Stream

```nim
type Process = object
  pid: int32      # offset 0
  ppid: int32     # offset 4
  memory: uint64  # offset 8
  cpu: float32    # offset 16
  # Total: 20 bytes per record
```

### Pipeline Operations

```bash
# Filter by predicate (type-safe!)
$ ps | where .memory > 1GB

# Project specific fields
$ ps | select .pid, .name

# Sort by field
$ ps | sort by .memory desc | take 10

# Aggregate
$ ps | group by .user | sum .memory

# Join streams
$ ps | join netstat on .pid

# Inspect schema
$ ps | inspect
# Shows: Schema + Binary hex dump

# Query with SQL
$ query "SELECT name, memory FROM processes WHERE cpu > 50"
```

---

## 🛠️ Quick Start

### Build Userland Utilities

```bash
# Install dependencies
sudo apt install nasm gcc ld python3

# Build all utilities
make userland

# Test them
./bin/echo          # Hello from Mini-Nim echo!
echo "test" | ./bin/cat
./bin/true && echo "Success: $?"
./bin/false || echo "Failed: $?"

# Try the text editor!
./bin/edit          # Opens file.txt in a beautiful CLI editor
# Type text, Backspace to delete, Ctrl+S to save, Ctrl+Q to quit
```

### Try the Type-Aware Shell! ⭐ NEW

```bash
# Launch the PoodillionOS Shell
./bin/psh

# The shell automatically detects and formats structured data!
psh> bin/ps

┌─── Schema ───────────────────────┐
│ Magic:   PSCH                     │
│ Version: 1                        │
│ Fields:  3                        │
│ RecSize: 12 bytes                 │
└──────────────────────────────────┘

┌─── Data (3 records) ───────────────┐
│ [0] 01 00 00 00 00 04 00 00 00 00 00 00  │
│ [1] 64 00 00 00 00 08 00 00 00 00 00 00  │
│ [2] c8 00 00 00 00 10 00 00 00 00 00 00  │
└──────────────────────────────────┘
```

### Try Data Pipeline (fully working!)

```bash
# Generate structured data (binary with schema)
./bin/ps | xxd
# 00000000: 5053 4348 0103 0c00 0300 0000 0100 0000  PSCH............
# 00000010: 0004 0000 0000 0000 6400 0000 0008 0000  ........d.......

# Or use the shell for automatic formatting!
echo "bin/ps" | ./bin/psh  # Pretty tables automatically!

# Inspect schema and data
./bin/ps | ./bin/inspect
# === Structured Data Stream ===
# Magic: PSCH
# Version: 01
# Fields: 03
# === Binary Data ===
# 03 00 00 00 01 00 00 00 00 04 00 00  # pid=1, mem=1024
# 64 00 00 00 00 08 00 00 00 00 00 00  # pid=100, mem=2048
# c8 00 00 00 00 10 00 00 00 00 00 00  # pid=200, mem=4096

# Filter with where command! 🎉
./bin/ps | ./bin/where | ./bin/inspect
# === Binary Data ===
# 03 00 00 00 64 00 00 00 00 08 00 00  # pid=100 (filtered out pid=1)
# c8 00 00 00 00 10 00 00 00 00 00 00  # pid=200

# Count records
./bin/ps | ./bin/count
# Record count: 3

# Compose pipelines!
./bin/ps | ./bin/where | ./bin/count
# Record count: 2  (filtered)

./bin/ps | ./bin/head | ./bin/inspect
# Shows only first record (pid=1)

./bin/ps | ./bin/tail | ./bin/inspect
# Shows only last record (pid=200)

./bin/ps | ./bin/where | ./bin/head | ./bin/inspect
# Shows first filtered record (pid=100)

./bin/ps | ./bin/where | ./bin/tail | ./bin/inspect
# Shows last filtered record (pid=200)

./bin/ps | ./bin/select | ./bin/inspect
# Projects only field 0 (pid): 1, 100, 200

./bin/ps | ./bin/where | ./bin/select | ./bin/count
# Filter then project: 2 records with 1 field each
```

### Build Kernel (optional)

```bash
# Build and run Mini-Nim kernel
make run-grub-mininim

# Or just the userland
make userland
```

---

## 📁 Project Structure

```
poodillion2/
├── compiler/           # Mini-Nim Compiler
│   ├── mininim.py     # Compiler driver
│   ├── lexer.py       # Tokenizer
│   ├── parser.py      # Parser (indentation-aware)
│   └── codegen_x86.py # x86 code generator
│
├── lib/               # System Libraries
│   ├── syscalls.nim   # Syscall wrappers (45+)
│   ├── syscalls.asm   # Assembly syscall stubs
│   └── schema.nim     # Data schema definitions
│
├── userland/          # Unix Utilities
│   ├── psh.nim        # ✅ Type-Aware Shell! 🎨
│   ├── echo.nim       # ✅ Working
│   ├── cat.nim        # ✅ Working
│   ├── edit.nim       # ✅ Working (text editor)
│   ├── true.nim       # ✅ Working
│   ├── false.nim      # ✅ Working
│   ├── ps.nim         # ✅ Working (binary output)
│   ├── inspect.nim    # ✅ Working (schema viewer)
│   ├── where.nim      # ✅ Working (data filter)
│   ├── count.nim      # ✅ Working (count records)
│   ├── head.nim       # ✅ Working (take first N)
│   ├── tail.nim       # ✅ Working (take last N)
│   └── select.nim     # ✅ Working (field projection)
│
├── bin/               # Compiled executables
│   ├── psh            # 13KB ELF32 - Type-Aware Shell! 🎨
│   ├── echo           # 8.9KB ELF32
│   ├── cat            # 5.1KB ELF32
│   ├── edit           # 11KB ELF32 - Text Editor!
│   ├── true           # 4.8KB ELF32
│   ├── false          # 4.8KB ELF32
│   ├── ps             # 8.8KB ELF32
│   ├── inspect        # 9.6KB ELF32
│   ├── where          # 9.7KB ELF32
│   ├── count          # 9.3KB ELF32
│   ├── head           # 9.1KB ELF32
│   ├── tail           # 9.2KB ELF32
│   └── select         # 9.0KB ELF32
│
├── kernel/            # OS Kernel (optional)
│   ├── kernel.c       # C kernel
│   └── shell_nim.nim  # Mini-Nim shell
│
├── boot/              # Bootloader
│   └── multiboot.asm  # GRUB multiboot
│
├── VISION.md          # 📖 Full vision document
└── Makefile           # Build system
```

---

## 🎯 Vision & Roadmap

See **[VISION.md](VISION.md)** for the complete vision.

### Phase 1: Core Infrastructure ✅ COMPLETE

- [x] Mini-Nim compiler with type system
- [x] Syscall library (45+ syscalls)
- [x] Basic utilities (echo, cat, true, false)
- [x] Binary schema format definition
- [x] Prototype structured data tools

### Phase 2: Data Pipeline ✅ COMPLETE!

- [x] **Fix binary I/O** - Address-of operator implemented ✅
- [x] **Size-aware codegen** - Proper byte/word/dword operations ✅
- [x] **Working pipeline** - ps | inspect fully functional ✅
- [x] **`where` command** - Filtering implemented! (hardcoded for now) ✅
- [x] **`count` command** - Count records in stream ✅
- [x] **`head` command** - Take first N records ✅
- [x] **`tail` command** - Take last N records ✅
- [x] **`select` command** - Field projection ✅
- [x] **`psh` shell** - Type-aware shell with automatic schema detection! ✅ 🎨
- [ ] **Command-line args** - Parse filter expressions from args
- [ ] **`sort` command** - Order by fields
- [ ] **Pipeline support in shell** - Parse and execute `cmd1 | cmd2` syntax

### Phase 3: Query Engine

- [ ] **SQL parser** - SELECT/WHERE/GROUP BY/JOIN
- [ ] **Query optimizer** - Push-down predicates
- [ ] **Index support** - Binary search on sorted data
- [ ] **Aggregation** - SUM/COUNT/AVG/etc

### Phase 4: Virtual Filesystem

- [ ] **/proc as objects** - `Process{pid, name, mem}`
- [ ] **/net as objects** - `Interface{ip, packets}`
- [ ] **/sys as objects** - `CPU{temp, load}`
- [ ] **Live queries** - SELECT from virtual tables

### Phase 5: Advanced Features

- [ ] **Time-travel shell** - Record all commands + data
- [ ] **Schema evolution** - Handle version changes
- [ ] **Distributed queries** - Query across machines
- [ ] **Zero-copy mmap** - Shared memory pipelines

---

## 🔧 Development

### Build Individual Utilities

```bash
# Build specific utility
make bin/echo
make bin/cat

# Build all
make userland

# Clean
rm -rf bin/
```

### Compiler Pipeline

```
source.nim → Mini-Nim Lexer → Tokens
           → Parser → AST
           → CodeGen → x86 Assembly (.asm)
           → NASM → Object file (.o)
           → LD + syscalls.o → ELF executable
```

### Mini-Nim Language Features

- **Types**: int32, uint32, int64, uint64, float32, bool, char, ptr T
- **Control**: if/elif/else, while, for i in start..end
- **Functions**: proc with params and return types
- **Operators**: +, -, *, /, %, ==, !=, <, >, <=, >=, &, |, ^, <<, >>
- **Memory**: cast, pointer arithmetic, syscalls
- **No GC**: Manual memory (brk/mmap)

---

## 🚀 Next Steps

### Immediate Priorities

1. **Add pipeline support to `psh` shell** ⬅ NEXT
   ```bash
   psh> bin/ps | bin/where | bin/select
   # Parse pipe syntax, create child processes, connect with pipes
   # Execute pipeline and display final output
   ```

2. **Add command-line arguments to utilities**
   ```bash
   $ ps | where 0 > 100      # Filter field 0 (pid) > 100
   $ ps | where 1 < 5000     # Filter field 1 (memory) < 5000
   $ ps | select 0 1         # Select fields 0 and 1
   $ ps | head 5             # Take first 5 records
   # Parse field_index, operator, value from command line
   ```

3. **Implement `sort` utility**
   ```bash
   $ ps | sort 0             # Sort by field 0 (pid)
   $ ps | sort 1 desc        # Sort by field 1 (memory) descending
   # Read all records, sort in memory, output sorted stream
   ```

4. **Add more source utilities**
   - `ls` - List files as structured data
   - Real `/proc` parsing for `ps`
   - `netstat` - Network connections

### Medium Term

- **Enhanced shell features** - Command history, tab completion, PATH resolution
- **Real `/proc` integration** - Read actual process data
- **Schema versioning** - Handle format changes
- **Performance testing** - Benchmark vs Unix pipes
- **Error messages** - Better diagnostics when pipelines fail

### Long Term

- **SQL query engine** - Full relational ops
- **Distributed mode** - Query cluster nodes
- **Time-travel** - Replay command history
- **Self-hosting** - Rewrite compiler in Mini-Nim

---

## 📚 Documentation

- **[VISION.md](VISION.md)** - Complete vision for data-oriented OS
- **[lib/syscalls.nim](lib/syscalls.nim)** - Available syscalls
- **[lib/schema.nim](lib/schema.nim)** - Data format specification

### Example Code

**Simple Utility (true.nim)**:
```nim
const SYS_exit: int32 = 1
extern proc syscall1(num: int32, arg1: int32): int32

proc main() =
  discard syscall1(SYS_exit, 0)
```

**Data Producer (ps.nim)**:
```nim
proc write_schema_header() =
  # Magic: "PSCH"
  discard syscall3(SYS_write, STDOUT, cast[int32]("PSCH"), 4)

  # Version: 1 (using addr operator for local variables!)
  var version: uint8 = 1
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(version)), 1)

  # Field count and record size...
  var field_count: uint8 = 3
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(field_count)), 1)

proc write_process_record(pid: int32, mem: int32) =
  # Binary output - no text! Using addr for safe pointer operations
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(pid)), 4)
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(mem)), 4)
```

---

## 🤝 Contributing

Want to help build the future of operating systems?

**Easy Tasks**:
- Add more basic utilities (ls, wc, grep)
- Improve shell error messages
- Add color support to shell output
- Test on different Linux distros
- Write more example pipelines

**Medium Tasks**:
- Add command-line arguments to utilities
- Implement pipeline parsing in shell
- Add real `/proc` parsing to `ps`
- Create schema validation tool
- Implement tab completion in shell
- Add command history with arrow keys

**Hard Tasks**:
- SQL query parser
- Schema evolution system
- Zero-copy mmap pipelines
- Distributed query engine

See [GitHub Issues](https://github.com/yourusername/poodillion2/issues) for specific tasks.

---

## 📜 License

**GPL-3.0** - See [LICENSE](LICENSE)

All code is free software. Fork it, hack it, improve it!

---

## 🌟 Status Summary

```
Project:    PoodillionOS - Data-Oriented Operating System
Language:   Mini-Nim (custom compiled language)
Runtime:    Zero dependencies (no libc, no stdlib)
Utilities:  13 working + Type-Aware Shell!
            (echo, cat, edit, true, false, ps, inspect, where, count, head, tail, select, psh)
Size:       ~121KB total for all utilities
Platform:   Linux x86/x86_64 (32-bit executables)
Status:     🚧 Active Development

Vision:     Unix performance + PowerShell composability
Innovation: Binary typed data streams, not text
Goal:       Type-safe, zero-copy, SQL-queryable OS

✅ Working:  Type-aware shell with automatic schema detection and pretty formatting!
✅ Working:  Full data pipeline! (ps | where | select | head | tail | count | inspect)
Next:       Pipeline composition in shell, command-line args parsing
```

**Try it now**:
```bash
git clone https://github.com/yourusername/poodillion2.git
cd poodillion2
make userland

# Try the type-aware shell!
./bin/psh
psh> bin/ps
# See beautiful schema tables automatically!

# Or use classic pipelines
./bin/ps | ./bin/where | ./bin/count
echo "Hello" | ./bin/cat
```

---

**Built with ❤️ and pure x86 assembly**

*PoodillionOS - Rethinking Unix from First Principles*
