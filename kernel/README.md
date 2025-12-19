# BrainhairOS Kernel

Microkernel written in C/Rust providing core OS functionality.

## Components

- **Memory Management**: Page allocator, virtual memory, heap
- **Process Scheduler**: Round-robin scheduler with process table
- **System Calls**: Interface between kernel and userspace
- **Device Drivers**: VGA, keyboard, serial, disk, network
- **TTY Subsystem**: Virtual terminals with line discipline

## Build

```bash
make kernel
```

## Status

🚧 **In Development** - Kernel code will be written here
