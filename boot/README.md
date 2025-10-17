# PoodillionOS Bootloader

GRUB multiboot2 configuration and boot assembly.

## Files

- `boot.asm` - x86_64 bootloader assembly
- `grub.cfg` - GRUB configuration
- `linker.ld` - Kernel linker script

## Boot Sequence

1. GRUB loads kernel at 1MB
2. boot.asm sets up long mode (64-bit)
3. Jumps to kernel_main()
4. Kernel initializes memory, processes, devices
5. Spawns /sbin/init
6. System ready

## Building Boot Image

```bash
make iso
qemu-system-x86_64 -cdrom poodillion.iso
```
