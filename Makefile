# Makefile for BrainhairOS
# Builds custom bootloader, kernel, and disk image

# Toolchain
AS = nasm
CC = gcc
LD = ld
NIM = nim

# Flags
ASFLAGS_16 = -f bin
ASFLAGS_32 = -f elf32
CFLAGS = -m32 -std=gnu99 -ffreestanding -O2 -Wall -Wextra -fno-exceptions -nostdlib
LDFLAGS = -m elf_i386 -T boot/linker.ld --no-relax

# Directories
BOOT_DIR = boot
KERNEL_DIR = kernel
NIM_DIR = nim
BUILD_DIR = build

# Output files
STAGE1_BIN = $(BUILD_DIR)/stage1.bin
STAGE2_BIN = $(BUILD_DIR)/stage2.bin
KERNEL_BIN = $(BUILD_DIR)/kernel.bin
DISK_IMG = $(BUILD_DIR)/brainhair.img

# Source files
STAGE1_ASM = $(BOOT_DIR)/stage1.asm
STAGE2_ASM = $(BOOT_DIR)/stage2.asm
BOOT_ASM = $(BOOT_DIR)/boot.asm
KERNEL_C = $(KERNEL_DIR)/kernel.c
KERNEL_NIM = $(NIM_DIR)/kernel.bh

# Object files
BOOT_OBJ = $(BUILD_DIR)/boot.o
KERNEL_OBJ = $(BUILD_DIR)/kernel.o

# Default target
.PHONY: all
all: $(DISK_IMG)

# Create build directory
$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

# Build stage 1 bootloader (MBR)
$(STAGE1_BIN): $(STAGE1_ASM) | $(BUILD_DIR)
	@echo "Building Stage 1 bootloader..."
	$(AS) $(ASFLAGS_16) $(STAGE1_ASM) -o $(STAGE1_BIN)
	@echo "  Size: $$(stat -c%s $(STAGE1_BIN)) bytes (must be 512)"

# Build stage 2 bootloader
$(STAGE2_BIN): $(STAGE2_ASM) | $(BUILD_DIR)
	@echo "Building Stage 2 bootloader..."
	$(AS) $(ASFLAGS_16) $(STAGE2_ASM) -o $(STAGE2_BIN)
	@echo "  Size: $$(stat -c%s $(STAGE2_BIN)) bytes"

# Assemble boot code for kernel
$(BOOT_OBJ): $(BOOT_ASM) | $(BUILD_DIR)
	@echo "Assembling kernel boot code..."
	$(AS) $(ASFLAGS_32) $(BOOT_ASM) -o $(BOOT_OBJ)

# Compile kernel (C version)
$(KERNEL_OBJ): $(KERNEL_C) | $(BUILD_DIR)
	@echo "Compiling C kernel..."
	$(CC) $(CFLAGS) -c $(KERNEL_C) -o $(KERNEL_OBJ)

# Compile Brainhair kernel (for custom bootloader)
BRAINHAIR_KERNEL_OBJ = compiler/kernel_main.o
$(BRAINHAIR_KERNEL_OBJ): kernel/kernel_main.bh
	@echo "Compiling Brainhair microkernel..."
	cd compiler && python3 brainhair.py ../kernel/kernel_main.bh --kernel -o kernel_main

# Assembly support files for microkernel
SERIAL_OBJ = $(BUILD_DIR)/serial.o
IDT_OBJ = $(BUILD_DIR)/idt.o
ISR_OBJ = $(BUILD_DIR)/isr.o
PAGING_OBJ = $(BUILD_DIR)/paging.o
PROCESS_OBJ = $(BUILD_DIR)/process.o
IPC_OBJ = $(BUILD_DIR)/ipc.o
KEYBOARD_OBJ = $(BUILD_DIR)/keyboard.o
ELF_OBJ = $(BUILD_DIR)/elf.o
NET_OBJ = $(BUILD_DIR)/net.o
ATA_OBJ = $(BUILD_DIR)/ata.o
PIPE_OBJ = $(BUILD_DIR)/pipe.o
VFS_OBJ = $(BUILD_DIR)/vfs.o
SIGNAL_OBJ = $(BUILD_DIR)/signal.o
USERLAND_BINS_OBJ = $(BUILD_DIR)/userland_bins.o
KERNEL_ASM_OBJS = $(SERIAL_OBJ) $(IDT_OBJ) $(ISR_OBJ) $(PAGING_OBJ) $(PROCESS_OBJ) $(IPC_OBJ) $(KEYBOARD_OBJ) $(ELF_OBJ) $(NET_OBJ) $(ATA_OBJ) $(PIPE_OBJ) $(VFS_OBJ) $(SIGNAL_OBJ) $(USERLAND_BINS_OBJ)

$(SERIAL_OBJ): kernel/serial.asm | $(BUILD_DIR)
	@echo "Assembling serial driver..."
	$(AS) $(ASFLAGS_32) kernel/serial.asm -o $(SERIAL_OBJ)

$(IDT_OBJ): kernel/idt.asm | $(BUILD_DIR)
	@echo "Assembling IDT..."
	$(AS) $(ASFLAGS_32) kernel/idt.asm -o $(IDT_OBJ)

$(ISR_OBJ): kernel/isr.asm | $(BUILD_DIR)
	@echo "Assembling ISR..."
	$(AS) $(ASFLAGS_32) kernel/isr.asm -o $(ISR_OBJ)

$(PAGING_OBJ): kernel/paging.asm | $(BUILD_DIR)
	@echo "Assembling paging..."
	$(AS) $(ASFLAGS_32) kernel/paging.asm -o $(PAGING_OBJ)

$(PROCESS_OBJ): kernel/process.asm | $(BUILD_DIR)
	@echo "Assembling process management..."
	$(AS) $(ASFLAGS_32) kernel/process.asm -o $(PROCESS_OBJ)

$(IPC_OBJ): kernel/ipc.asm | $(BUILD_DIR)
	@echo "Assembling IPC..."
	$(AS) $(ASFLAGS_32) kernel/ipc.asm -o $(IPC_OBJ)

$(KEYBOARD_OBJ): kernel/keyboard.asm | $(BUILD_DIR)
	@echo "Assembling keyboard driver..."
	$(AS) $(ASFLAGS_32) kernel/keyboard.asm -o $(KEYBOARD_OBJ)

$(ELF_OBJ): kernel/elf.asm | $(BUILD_DIR)
	@echo "Assembling ELF loader..."
	$(AS) $(ASFLAGS_32) kernel/elf.asm -o $(ELF_OBJ)

$(NET_OBJ): kernel/net.asm | $(BUILD_DIR)
	@echo "Assembling network driver..."
	$(AS) $(ASFLAGS_32) kernel/net.asm -o $(NET_OBJ)

$(ATA_OBJ): kernel/ata.asm | $(BUILD_DIR)
	@echo "Assembling ATA driver..."
	$(AS) $(ASFLAGS_32) kernel/ata.asm -o $(ATA_OBJ)

$(PIPE_OBJ): kernel/pipe.asm | $(BUILD_DIR)
	@echo "Assembling pipe subsystem..."
	$(AS) $(ASFLAGS_32) kernel/pipe.asm -o $(PIPE_OBJ)

$(VFS_OBJ): kernel/vfs.asm | $(BUILD_DIR)
	@echo "Assembling VFS layer..."
	$(AS) $(ASFLAGS_32) kernel/vfs.asm -o $(VFS_OBJ)

$(SIGNAL_OBJ): kernel/signal.asm | $(BUILD_DIR)
	@echo "Assembling signal subsystem..."
	$(AS) $(ASFLAGS_32) kernel/signal.asm -o $(SIGNAL_OBJ)

# Build webapp binary first, then embed it (before USERLAND_DIR is defined)
$(BIN_DIR)/webapp: userland/webapp.bh lib/syscalls.o | $(BIN_DIR)
	@./bin/bhbuild userland/webapp.bh $(BIN_DIR)/webapp

$(USERLAND_BINS_OBJ): kernel/userland_bins.asm $(BIN_DIR)/webapp | $(BUILD_DIR)
	@echo "Embedding userland binaries..."
	$(AS) $(ASFLAGS_32) kernel/userland_bins.asm -o $(USERLAND_BINS_OBJ)

# Compile Brainhair kernel for GRUB
BRAINHAIR_KERNEL_OBJ_GRUB = $(BUILD_DIR)/kernel_brainhair.o
BRAINHAIR_WRAPPER_OBJ = $(BUILD_DIR)/brainhair_wrapper.o

$(BRAINHAIR_KERNEL_OBJ_GRUB): kernel/kernel.bh | $(BUILD_DIR)
	@echo "Compiling Brainhair kernel for GRUB..."
	cd compiler && python3 brainhair.py ../kernel/kernel.bh --kernel -o kernel_brainhair
	@mv compiler/kernel_brainhair.o $(BRAINHAIR_KERNEL_OBJ_GRUB)
	@echo "  Brainhair kernel compiled: $(BRAINHAIR_KERNEL_OBJ_GRUB)"

$(BRAINHAIR_WRAPPER_OBJ): kernel/brainhair_wrapper.asm | $(BUILD_DIR)
	@echo "Assembling Brainhair wrapper..."
	$(AS) $(ASFLAGS_32) kernel/brainhair_wrapper.asm -o $(BRAINHAIR_WRAPPER_OBJ)

# Build kernel with Brainhair compiler
.PHONY: kernel-brainhair
kernel-brainhair: $(BOOT_OBJ) $(BRAINHAIR_KERNEL_OBJ) $(KERNEL_ASM_OBJS)
	@echo "Linking Brainhair kernel..."
	$(LD) $(LDFLAGS) -o $(BUILD_DIR)/kernel.elf $(BOOT_OBJ) $(BRAINHAIR_KERNEL_OBJ) $(KERNEL_ASM_OBJS)
	@echo "Converting ELF to flat binary..."
	objcopy -O binary $(BUILD_DIR)/kernel.elf $(KERNEL_BIN)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_BIN)) bytes"

# Compile Nim kernel
.PHONY: kernel-nim
kernel-nim: $(BUILD_DIR)
	@echo "Compiling Nim kernel..."
	cd $(NIM_DIR) && $(NIM) c --nimcache:../$(BUILD_DIR)/nimcache -c kernel.bh
	@echo "Compiling generated C code..."
	$(CC) $(CFLAGS) -I$(NIM_DIR) -c $(BUILD_DIR)/nimcache/*.c -o $(BUILD_DIR)/kernel_nim.o 2>/dev/null || true
	@echo "Nim kernel compiled!"

# Link kernel
$(KERNEL_BIN): $(BOOT_OBJ) $(KERNEL_OBJ)
	@echo "Linking kernel..."
	$(LD) $(LDFLAGS) -o $(BUILD_DIR)/kernel.elf $(BOOT_OBJ) $(KERNEL_OBJ)
	@echo "Converting ELF to flat binary..."
	objcopy -O binary $(BUILD_DIR)/kernel.elf $(KERNEL_BIN)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_BIN)) bytes"

# Create bootable disk image
$(DISK_IMG): $(STAGE1_BIN) $(STAGE2_BIN) $(KERNEL_BIN)
	@echo "Creating disk image..."
	# Create 10MB disk image
	dd if=/dev/zero of=$(DISK_IMG) bs=512 count=20480 2>/dev/null
	# Write stage 1 to MBR (sector 0)
	dd if=$(STAGE1_BIN) of=$(DISK_IMG) conv=notrunc bs=512 count=1 2>/dev/null
	# Write stage 2 (sector 1-16)
	dd if=$(STAGE2_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=1 2>/dev/null
	# Write kernel (sector 18+)
	dd if=$(KERNEL_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=18 2>/dev/null
	@echo "Disk image created: $(DISK_IMG)"
	@echo "  Size: $$(stat -c%s $(DISK_IMG)) bytes"

# Build full disk image with Brainhair kernel
.PHONY: brainhair
brainhair: $(STAGE1_BIN) $(STAGE2_BIN) kernel-brainhair
	@echo "Creating disk image with Brainhair kernel..."
	dd if=/dev/zero of=$(DISK_IMG) bs=512 count=20480 2>/dev/null
	dd if=$(STAGE1_BIN) of=$(DISK_IMG) conv=notrunc bs=512 count=1 2>/dev/null
	dd if=$(STAGE2_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=1 2>/dev/null
	dd if=$(KERNEL_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=18 2>/dev/null
	@echo "✓ Brainhair disk image created: $(DISK_IMG)"
	@echo "  Kernel: Brainhair compiled!"
	@echo "  Run with: make run"

# ========== MICROKERNEL TARGETS ==========

# Build and run the BrainhairOS microkernel
.PHONY: microkernel
microkernel: $(STAGE1_BIN) $(STAGE2_BIN) $(BRAINHAIR_KERNEL_OBJ) $(BOOT_OBJ) $(IDT_OBJ) $(ISR_OBJ) $(PAGING_OBJ) $(PROCESS_OBJ) $(SERIAL_OBJ) $(IPC_OBJ) $(KEYBOARD_OBJ) $(ELF_OBJ) $(NET_OBJ) $(ATA_OBJ) $(PIPE_OBJ) $(VFS_OBJ) $(SIGNAL_OBJ)
	@echo "Building BrainhairOS Microkernel..."
	$(LD) $(LDFLAGS) -o $(BUILD_DIR)/kernel.elf $(BOOT_OBJ) $(SERIAL_OBJ) $(IDT_OBJ) $(ISR_OBJ) $(PAGING_OBJ) $(PROCESS_OBJ) $(IPC_OBJ) $(KEYBOARD_OBJ) $(ELF_OBJ) $(NET_OBJ) $(ATA_OBJ) $(PIPE_OBJ) $(VFS_OBJ) $(SIGNAL_OBJ) $(BRAINHAIR_KERNEL_OBJ)
	objcopy -O binary $(BUILD_DIR)/kernel.elf $(KERNEL_BIN)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_BIN)) bytes"
	dd if=/dev/zero of=$(DISK_IMG) bs=512 count=20480 2>/dev/null
	dd if=$(STAGE1_BIN) of=$(DISK_IMG) conv=notrunc bs=512 count=1 2>/dev/null
	dd if=$(STAGE2_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=1 2>/dev/null
	dd if=$(KERNEL_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=18 2>/dev/null
	@echo ""
	@echo "✓ BrainhairOS Microkernel built!"
	@echo "  Disk image: $(DISK_IMG)"
	@echo "  Run with: make run-microkernel"

# Microkernel with embedded userland webapp
.PHONY: microkernel-uweb
microkernel-uweb: $(STAGE1_BIN) $(STAGE2_BIN) $(BRAINHAIR_KERNEL_OBJ) $(BOOT_OBJ) $(IDT_OBJ) $(ISR_OBJ) $(PAGING_OBJ) $(PROCESS_OBJ) $(SERIAL_OBJ) $(IPC_OBJ) $(KEYBOARD_OBJ) $(ELF_OBJ) $(NET_OBJ) $(ATA_OBJ) $(USERLAND_BINS_OBJ)
	@echo "Building BrainhairOS Microkernel with embedded webapp..."
	$(LD) $(LDFLAGS) -o $(BUILD_DIR)/kernel.elf $(BOOT_OBJ) $(SERIAL_OBJ) $(IDT_OBJ) $(ISR_OBJ) $(PAGING_OBJ) $(PROCESS_OBJ) $(IPC_OBJ) $(KEYBOARD_OBJ) $(ELF_OBJ) $(NET_OBJ) $(ATA_OBJ) $(BRAINHAIR_KERNEL_OBJ) $(USERLAND_BINS_OBJ)
	objcopy -O binary $(BUILD_DIR)/kernel.elf $(KERNEL_BIN)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_BIN)) bytes"
	dd if=/dev/zero of=$(DISK_IMG) bs=512 count=20480 2>/dev/null
	dd if=$(STAGE1_BIN) of=$(DISK_IMG) conv=notrunc bs=512 count=1 2>/dev/null
	dd if=$(STAGE2_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=1 2>/dev/null
	dd if=$(KERNEL_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=18 2>/dev/null
	@echo ""
	@echo "✓ BrainhairOS Microkernel built!"
	@echo "  Disk image: $(DISK_IMG)"
	@echo "  Run with: make run-microkernel"

.PHONY: run-microkernel
run-microkernel: microkernel
	@echo "Booting BrainhairOS Microkernel..."
	qemu-system-i386 -drive file=$(DISK_IMG),format=raw \
		-device e1000,netdev=net0 -netdev user,id=net0

.PHONY: run-microkernel-serial
run-microkernel-serial: microkernel
	@echo "Booting BrainhairOS Microkernel (serial output)..."
	@echo "Press Ctrl-A X to exit QEMU"
	@echo "========================================"
	qemu-system-i386 -drive file=$(DISK_IMG),format=raw -display none -serial stdio \
		-device e1000,netdev=net0 -netdev user,id=net0

# Build just the kernel
.PHONY: kernel
kernel: $(KERNEL_BIN)

# Build bootloader only
.PHONY: bootloader
bootloader: $(STAGE1_BIN) $(STAGE2_BIN)

# Run in QEMU
.PHONY: run
run: $(DISK_IMG)
	@echo "Booting BrainhairOS in QEMU..."
	qemu-system-i386 -drive file=$(DISK_IMG),format=raw

# Run with debugging output
.PHONY: run-debug
run-debug: $(DISK_IMG)
	@echo "Booting BrainhairOS in QEMU (debug mode)..."
	qemu-system-i386 -drive file=$(DISK_IMG),format=raw -serial stdio -d cpu_reset

# Run with GDB debugging
.PHONY: debug
debug: $(DISK_IMG)
	@echo "Starting QEMU with GDB server..."
	@echo "Connect with: gdb -ex 'target remote localhost:1234' -ex 'break *0x7c00'"
	qemu-system-i386 -drive file=$(DISK_IMG),format=raw -s -S

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)

# Check required tools
.PHONY: check-tools
check-tools:
	@echo "Checking required tools..."
	@which $(AS) > /dev/null || (echo "ERROR: nasm not found. Install: sudo apt install nasm" && exit 1)
	@which $(CC) > /dev/null || (echo "ERROR: gcc not found. Install: sudo apt install gcc" && exit 1)
	@which $(LD) > /dev/null || (echo "ERROR: ld not found. Install: sudo apt install binutils" && exit 1)
	@which qemu-system-i386 > /dev/null || (echo "WARNING: qemu not found. Install: sudo apt install qemu-system-x86")
	@which dd > /dev/null || (echo "ERROR: dd not found (should be in coreutils)")
	@echo "✓ All required tools are installed!"

# ========== GRUB MULTIBOOT TARGETS ==========

# GRUB-specific variables
ISO_DIR = $(BUILD_DIR)/iso
GRUB_DIR = $(ISO_DIR)/boot/grub
MULTIBOOT_ASM = $(BOOT_DIR)/multiboot.asm
MULTIBOOT_OBJ = $(BUILD_DIR)/multiboot.o
LINKER_GRUB = $(BOOT_DIR)/linker_grub.ld
KERNEL_ELF = $(ISO_DIR)/boot/kernel.elf
GRUB_ISO = $(BUILD_DIR)/brainhair_grub.iso

# Build multiboot kernel for GRUB (C version)
$(KERNEL_ELF): $(MULTIBOOT_OBJ) $(KERNEL_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building multiboot kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_ELF) $(MULTIBOOT_OBJ) $(KERNEL_OBJ)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_ELF)) bytes"

# Build Brainhair multiboot kernel for GRUB
KERNEL_BRAINHAIR_ELF = $(ISO_DIR)/boot/kernel_brainhair.elf
$(KERNEL_BRAINHAIR_ELF): $(MULTIBOOT_OBJ) $(BRAINHAIR_KERNEL_OBJ_GRUB) $(SERIAL_OBJ) $(BRAINHAIR_WRAPPER_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building Brainhair multiboot kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_BRAINHAIR_ELF) $(MULTIBOOT_OBJ) $(BRAINHAIR_WRAPPER_OBJ) $(SERIAL_OBJ) $(BRAINHAIR_KERNEL_OBJ_GRUB)
	@echo "  Brainhair Kernel size: $$(stat -c%s $(KERNEL_BRAINHAIR_ELF)) bytes"

$(MULTIBOOT_OBJ): $(MULTIBOOT_ASM) | $(BUILD_DIR)
	@echo "Assembling multiboot header..."
	$(AS) $(ASFLAGS_32) $(MULTIBOOT_ASM) -o $(MULTIBOOT_OBJ)

$(GRUB_DIR):
	@mkdir -p $(GRUB_DIR)
	@echo "set timeout=0" > $(GRUB_DIR)/grub.cfg
	@echo "set default=0" >> $(GRUB_DIR)/grub.cfg
	@echo "" >> $(GRUB_DIR)/grub.cfg
	@echo 'menuentry "BrainhairOS" {' >> $(GRUB_DIR)/grub.cfg
	@echo "    multiboot /boot/kernel.elf" >> $(GRUB_DIR)/grub.cfg
	@echo "    boot" >> $(GRUB_DIR)/grub.cfg
	@echo "}" >> $(GRUB_DIR)/grub.cfg

# Build bootable GRUB ISO
$(GRUB_ISO): $(KERNEL_ELF)
	@echo "Creating bootable GRUB ISO..."
	@grub-mkrescue -o $(GRUB_ISO) $(ISO_DIR) 2>&1 | grep -v "^xorriso" || true
	@echo "  ISO created: $(GRUB_ISO)"

.PHONY: grub
grub: $(GRUB_ISO)
	@echo "✓ GRUB ISO ready!"
	@echo "  Boot with: make run-grub"

.PHONY: run-grub
run-grub: $(KERNEL_ELF)
	@echo "Booting BrainhairOS with GRUB (multiboot)..."
	@echo "Serial output below (Ctrl-C to exit):"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_ELF) -display none -serial stdio

# Brainhair kernel targets
.PHONY: grub-brainhair
grub-brainhair: $(KERNEL_BRAINHAIR_ELF)
	@echo "✓ Brainhair kernel ready!"
	@echo "  Boot with: make run-grub-brainhair"

.PHONY: run-grub-brainhair
run-grub-brainhair: $(KERNEL_BRAINHAIR_ELF)
	@echo "Booting BrainhairOS Brainhair Kernel with GRUB..."
	@echo "Serial output below (Ctrl-C to exit):"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_BRAINHAIR_ELF) -display none -serial stdio

.PHONY: run-grub-brainhair-gui
run-grub-brainhair-gui: $(KERNEL_BRAINHAIR_ELF)
	@echo "Booting BrainhairOS Brainhair Kernel with GRUB (GUI)..."
	qemu-system-i386 -kernel $(KERNEL_BRAINHAIR_ELF)

# Interactive Shell kernel targets (uses KEYBOARD_OBJ from above)
VGA_OBJ = $(BUILD_DIR)/vga.o
SHELL_OBJ = $(BUILD_DIR)/shell.o
SHELL_WRAPPER_OBJ = $(BUILD_DIR)/shell_wrapper.o
KERNEL_SHELL_ELF = $(ISO_DIR)/boot/kernel_shell.elf

$(VGA_OBJ): kernel/vga.asm | $(BUILD_DIR)
	@echo "Assembling VGA driver..."
	$(AS) $(ASFLAGS_32) kernel/vga.asm -o $(VGA_OBJ)

$(SHELL_OBJ): kernel/shell.asm | $(BUILD_DIR)
	@echo "Assembling shell..."
	$(AS) $(ASFLAGS_32) kernel/shell.asm -o $(SHELL_OBJ)

$(SHELL_WRAPPER_OBJ): kernel/shell_wrapper.asm | $(BUILD_DIR)
	@echo "Assembling shell wrapper..."
	$(AS) $(ASFLAGS_32) kernel/shell_wrapper.asm -o $(SHELL_WRAPPER_OBJ)

$(KERNEL_SHELL_ELF): $(MULTIBOOT_OBJ) $(SERIAL_OBJ) $(KEYBOARD_OBJ) $(VGA_OBJ) $(SHELL_OBJ) $(SHELL_WRAPPER_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building interactive shell kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_SHELL_ELF) $(MULTIBOOT_OBJ) $(SHELL_WRAPPER_OBJ) $(SERIAL_OBJ) $(VGA_OBJ) $(KEYBOARD_OBJ) $(SHELL_OBJ)
	@echo "  Shell Kernel size: $$(stat -c%s $(KERNEL_SHELL_ELF)) bytes"

.PHONY: shell
shell: $(KERNEL_SHELL_ELF)
	@echo "✓ Interactive shell kernel ready!"
	@echo "  Boot with: make run-shell"

.PHONY: run-shell
run-shell: $(KERNEL_SHELL_ELF)
	@echo "Booting BrainhairOS Interactive Shell..."
	@echo "========================================"
	@echo "Type commands and press Enter."
	@echo "Try: help, clear, echo, ls, ps, uname"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_SHELL_ELF)

.PHONY: run-shell-serial
run-shell-serial: $(KERNEL_SHELL_ELF)
	@echo "Booting BrainhairOS Interactive Shell (with serial)..."
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_SHELL_ELF) -serial stdio

# Serial-based Shell kernel (assembly only for now)
SHELL_SERIAL_OBJ = $(BUILD_DIR)/shell_serial.o
KERNEL_SERIAL_SHELL_ELF = $(ISO_DIR)/boot/kernel_serial_shell.elf

$(SHELL_SERIAL_OBJ): kernel/shell_serial.asm | $(BUILD_DIR)
	@echo "Assembling serial shell..."
	$(AS) $(ASFLAGS_32) kernel/shell_serial.asm -o $(SHELL_SERIAL_OBJ)

$(KERNEL_SERIAL_SHELL_ELF): $(MULTIBOOT_OBJ) $(SERIAL_OBJ) $(SHELL_SERIAL_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building serial shell kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_SERIAL_SHELL_ELF) $(MULTIBOOT_OBJ) $(SHELL_SERIAL_OBJ) $(SERIAL_OBJ)
	@echo "  Serial Shell Kernel size: $$(stat -c%s $(KERNEL_SERIAL_SHELL_ELF)) bytes"

.PHONY: serial-shell
serial-shell: $(KERNEL_SERIAL_SHELL_ELF)
	@echo "✓ Serial shell kernel ready!"
	@echo "  Boot with: make run-serial-shell"

.PHONY: run-serial-shell
run-serial-shell: $(KERNEL_SERIAL_SHELL_ELF)
	@echo "Booting BrainhairOS Serial Shell..."
	@echo "Serial output below (Ctrl-C to exit):"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_SERIAL_SHELL_ELF) -display none -serial stdio

# Brainhair Shell kernel targets (VGA-based, kept for reference)
BRAINHAIR_SHELL_OBJ = $(BUILD_DIR)/shell_brainhair.o
BRAINHAIR_SHELL_WRAPPER_OBJ = $(BUILD_DIR)/brainhair_shell_wrapper.o
KERNEL_BRAINHAIR_SHELL_ELF = $(ISO_DIR)/boot/kernel_brainhair_shell.elf

$(BRAINHAIR_SHELL_OBJ): kernel/shell_brainhair.bh | $(BUILD_DIR)
	@echo "Compiling Brainhair shell kernel..."
	cd compiler && python3 brainhair.py ../kernel/shell_brainhair.bh --kernel -o shell_brainhair
	@mv compiler/shell_brainhair.o $(BRAINHAIR_SHELL_OBJ)
	@echo "  Brainhair shell compiled: $(BRAINHAIR_SHELL_OBJ)"

$(BRAINHAIR_SHELL_WRAPPER_OBJ): kernel/brainhair_shell_wrapper.asm | $(BUILD_DIR)
	@echo "Assembling Brainhair shell wrapper..."
	$(AS) $(ASFLAGS_32) kernel/brainhair_shell_wrapper.asm -o $(BRAINHAIR_SHELL_WRAPPER_OBJ)

$(KERNEL_BRAINHAIR_SHELL_ELF): $(MULTIBOOT_OBJ) $(SERIAL_OBJ) $(BRAINHAIR_SHELL_WRAPPER_OBJ) $(BRAINHAIR_SHELL_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building Brainhair shell kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_BRAINHAIR_SHELL_ELF) $(MULTIBOOT_OBJ) $(BRAINHAIR_SHELL_WRAPPER_OBJ) $(SERIAL_OBJ) $(BRAINHAIR_SHELL_OBJ)
	@echo "  Brainhair Shell Kernel size: $$(stat -c%s $(KERNEL_BRAINHAIR_SHELL_ELF)) bytes"

.PHONY: brainhair-shell
brainhair-shell: $(KERNEL_BRAINHAIR_SHELL_ELF)
	@echo "✓ Brainhair shell kernel ready!"
	@echo "  Boot with: make run-brainhair-shell"

.PHONY: run-brainhair-shell
run-brainhair-shell: $(KERNEL_BRAINHAIR_SHELL_ELF)
	@echo "Booting BrainhairOS Brainhair Shell (VGA)..."
	@echo "========================================"
	@echo "Shell written in Brainhair!"
	@echo "Commands: ls, cat, echo, help"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_BRAINHAIR_SHELL_ELF)

# NEW: Full Brainhair Shell with extern functions (SERIAL OUTPUT)
.PHONY: run-nim-shell
run-nim-shell: build/kernel_shell_nim.elf
	@echo "========================================"
	@echo "  BrainhairOS v0.1 - Brainhair Shell"
	@echo "========================================"
	@echo "Full OS shell written in Brainhair!"
	@echo "Commands: ls, cat, echo, help"
	@echo "Press Ctrl-C to exit"
	@echo "========================================"
	qemu-system-i386 -kernel build/kernel_shell_nim.elf -serial stdio -display none

# Build Brainhair shell kernel
build/kernel_shell_nim.elf: compiler/shell_nim.o build/multiboot.o build/serial.o kernel/brainhair_shell_wrapper.asm | $(BUILD_DIR)
	@echo "Building Brainhair shell kernel..."
	@nasm -f elf32 kernel/brainhair_shell_wrapper.asm -o build/wrapper_shell.o
	@ld -m elf_i386 -T boot/linker_grub.ld -o build/kernel_shell_nim.elf build/multiboot.o build/wrapper_shell.o build/serial.o compiler/shell_nim.o
	@echo "  Brainhair Shell Kernel: $$(stat -c%s build/kernel_shell_nim.elf) bytes"

compiler/shell_nim.o: kernel/shell_nim.bh
	@echo "Compiling Brainhair shell..."
	cd compiler && python3 brainhair.py ../kernel/shell_nim.bh --kernel -o shell_nim
	@echo "  Shell compiled: $$(stat -c%s compiler/shell_nim.o) bytes"

.PHONY: run-grub-iso
run-grub-iso: $(GRUB_ISO)
	@echo "Booting BrainhairOS from GRUB ISO..."
	qemu-system-i386 -cdrom $(GRUB_ISO)

# ========== USER LAND UTILITIES ==========

# Userland directories
USERLAND_DIR = userland
LIB_DIR = lib
BIN_DIR = bin

# Create bin directory
$(BIN_DIR):
	@mkdir -p $(BIN_DIR)

# Build syscall library (using self-hosted assembler)
$(LIB_DIR)/syscalls.o: $(LIB_DIR)/syscalls.asm | $(BUILD_DIR)
	@echo "Assembling syscall library..."
	@./bin/basm $(LIB_DIR)/syscalls.asm $(LIB_DIR)/syscalls.o

# Generic rule to compile userland utilities (using self-hosted toolchain)
$(BIN_DIR)/%: $(USERLAND_DIR)/%.bh $(LIB_DIR)/syscalls.o | $(BIN_DIR)
	@./bin/bhbuild $(USERLAND_DIR)/$*.bh $(BIN_DIR)/$*

# Core utilities (original)
CORE_UTILS = $(BIN_DIR)/echo $(BIN_DIR)/true $(BIN_DIR)/false $(BIN_DIR)/cat $(BIN_DIR)/edit

# Data pipeline utilities
DATA_UTILS = $(BIN_DIR)/ps $(BIN_DIR)/inspect $(BIN_DIR)/where $(BIN_DIR)/count $(BIN_DIR)/head $(BIN_DIR)/tail $(BIN_DIR)/select $(BIN_DIR)/sort $(BIN_DIR)/fmt $(BIN_DIR)/ls

# Graphics utilities
GRAPHICS_UTILS = $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/demo $(BIN_DIR)/pixel $(BIN_DIR)/line $(BIN_DIR)/rect $(BIN_DIR)/circle

# Graphical applications (desktop environment)
GRAPHICAL_APPS = $(BIN_DIR)/bds $(BIN_DIR)/term $(BIN_DIR)/fm $(BIN_DIR)/gedit $(BIN_DIR)/calc $(BIN_DIR)/sysmon $(BIN_DIR)/settings $(BIN_DIR)/imgview $(BIN_DIR)/hexview

# File manipulation utilities (new)
FILE_UTILS = $(BIN_DIR)/rm $(BIN_DIR)/mkdir $(BIN_DIR)/rmdir $(BIN_DIR)/mv $(BIN_DIR)/touch $(BIN_DIR)/cp $(BIN_DIR)/mkfifo $(BIN_DIR)/mknod $(BIN_DIR)/link $(BIN_DIR)/unlink $(BIN_DIR)/truncate $(BIN_DIR)/realpath

# Text processing utilities (new)
TEXT_UTILS = $(BIN_DIR)/wc $(BIN_DIR)/tee $(BIN_DIR)/rev $(BIN_DIR)/yes $(BIN_DIR)/seq $(BIN_DIR)/cut $(BIN_DIR)/uniq $(BIN_DIR)/tr $(BIN_DIR)/basename $(BIN_DIR)/dirname $(BIN_DIR)/ed $(BIN_DIR)/grep $(BIN_DIR)/sed

# Advanced text utilities
ADVANCED_TEXT_UTILS = $(BIN_DIR)/more $(BIN_DIR)/split $(BIN_DIR)/join $(BIN_DIR)/paste $(BIN_DIR)/nl

# String/formatting utilities
STRING_UTILS = $(BIN_DIR)/printf $(BIN_DIR)/fold $(BIN_DIR)/expand $(BIN_DIR)/unexpand $(BIN_DIR)/col $(BIN_DIR)/colrm

# System info utilities (new)
SYSINFO_UTILS = $(BIN_DIR)/uname $(BIN_DIR)/free $(BIN_DIR)/uptime $(BIN_DIR)/hostname $(BIN_DIR)/whoami $(BIN_DIR)/id $(BIN_DIR)/printenv $(BIN_DIR)/tty $(BIN_DIR)/nproc $(BIN_DIR)/arch $(BIN_DIR)/logname $(BIN_DIR)/groups $(BIN_DIR)/vmstat $(BIN_DIR)/iostat $(BIN_DIR)/lsof

# User management utilities
USER_MGMT_UTILS = $(BIN_DIR)/su $(BIN_DIR)/passwd $(BIN_DIR)/useradd $(BIN_DIR)/userdel $(BIN_DIR)/groupadd $(BIN_DIR)/chpasswd

# Process utilities (new)
PROC_UTILS = $(BIN_DIR)/kill $(BIN_DIR)/pidof $(BIN_DIR)/sleep $(BIN_DIR)/timeout $(BIN_DIR)/time $(BIN_DIR)/wait $(BIN_DIR)/renice $(BIN_DIR)/sync $(BIN_DIR)/usleep $(BIN_DIR)/pgrep $(BIN_DIR)/pkill $(BIN_DIR)/killall $(BIN_DIR)/nohup $(BIN_DIR)/nice

# Disk utilities (new)
DISK_UTILS = $(BIN_DIR)/df $(BIN_DIR)/du $(BIN_DIR)/stat $(BIN_DIR)/file $(BIN_DIR)/ln $(BIN_DIR)/readlink

# File search utilities
SEARCH_UTILS = $(BIN_DIR)/find $(BIN_DIR)/od $(BIN_DIR)/strings

# Time and permission utilities
TIME_PERM_UTILS = $(BIN_DIR)/date $(BIN_DIR)/chmod $(BIN_DIR)/chown $(BIN_DIR)/chgrp $(BIN_DIR)/pwd

# Shell scripting utilities
SHELL_SCRIPT_UTILS = $(BIN_DIR)/test $(BIN_DIR)/expr $(BIN_DIR)/which $(BIN_DIR)/xargs $(BIN_DIR)/env $(BIN_DIR)/getopt

# POSIX compliance utilities
POSIX_UTILS = $(BIN_DIR)/install $(BIN_DIR)/tsort $(BIN_DIR)/pathchk $(BIN_DIR)/mktemp $(BIN_DIR)/dircolors

# Diff/comparison utilities
DIFF_UTILS = $(BIN_DIR)/cmp $(BIN_DIR)/comm $(BIN_DIR)/diff

# Archive utilities
ARCHIVE_UTILS = $(BIN_DIR)/tar $(BIN_DIR)/cpio $(BIN_DIR)/ar

# Math and calculation utilities
MATH_UTILS = $(BIN_DIR)/factor $(BIN_DIR)/bc $(BIN_DIR)/sum $(BIN_DIR)/cksum $(BIN_DIR)/shuf

# Shell
SHELL_UTILS = $(BIN_DIR)/psh

# Terminal and I/O utilities

# Text display/formatting utilities
DISPLAY_UTILS = $(BIN_DIR)/pr $(BIN_DIR)/xxd $(BIN_DIR)/look $(BIN_DIR)/csplit $(BIN_DIR)/ptx
TERMINAL_UTILS = $(BIN_DIR)/stty $(BIN_DIR)/tput $(BIN_DIR)/reset $(BIN_DIR)/mesg $(BIN_DIR)/script

# Networking utilities
NET_UTILS = $(BIN_DIR)/netstat $(BIN_DIR)/ifconfig $(BIN_DIR)/route $(BIN_DIR)/dnsdomainname

# Kernel utilities
KERNEL_UTILS = $(BIN_DIR)/dmesg $(BIN_DIR)/lsmod $(BIN_DIR)/sysctl $(BIN_DIR)/modinfo $(BIN_DIR)/insmod $(BIN_DIR)/rmmod

# System control utilities
SYSTEM_UTILS = $(BIN_DIR)/mount $(BIN_DIR)/umount $(BIN_DIR)/shutdown $(BIN_DIR)/reboot $(BIN_DIR)/halt $(BIN_DIR)/poweroff

# Boot utilities (essential for system boot)
BOOT_UTILS = $(BIN_DIR)/init $(BIN_DIR)/getty $(BIN_DIR)/login

# All utilities
ALL_UTILS = $(CORE_UTILS) $(DATA_UTILS) $(GRAPHICS_UTILS) $(GRAPHICAL_APPS) $(FILE_UTILS) $(TEXT_UTILS) $(ADVANCED_TEXT_UTILS) $(STRING_UTILS) $(DISPLAY_UTILS) $(SYSINFO_UTILS) $(USER_MGMT_UTILS) $(PROC_UTILS) $(DISK_UTILS) $(SEARCH_UTILS) $(TIME_PERM_UTILS) $(SHELL_SCRIPT_UTILS) $(POSIX_UTILS) $(MATH_UTILS) $(DIFF_UTILS) $(ARCHIVE_UTILS) $(SHELL_UTILS) $(TERMINAL_UTILS) $(NET_UTILS) $(KERNEL_UTILS) $(SYSTEM_UTILS) $(BOOT_UTILS)

# Build all userland utilities
.PHONY: userland
userland: $(ALL_UTILS)
	@echo "✓ All userland utilities built!"
	@echo ""
	@echo "Core utilities:"
	@ls -lh $(CORE_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Data pipeline:"
	@ls -lh $(DATA_UTILS) 2>/dev/null || true
	@echo ""
	@echo "File utilities:"
	@ls -lh $(FILE_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Text utilities:"
	@ls -lh $(TEXT_UTILS) 2>/dev/null || true
	@echo ""
	@echo "System info:"
	@ls -lh $(SYSINFO_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Process utilities:"
	@ls -lh $(PROC_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Disk utilities:"
	@ls -lh $(DISK_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Search utilities:"
	@ls -lh $(SEARCH_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Time and permission utilities:"
	@ls -lh $(TIME_PERM_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Shell scripting utilities:"
	@ls -lh $(SHELL_SCRIPT_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Math utilities:"
	@ls -lh $(MATH_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Diff/comparison utilities:"
	@ls -lh $(DIFF_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Archive utilities:"
	@ls -lh $(ARCHIVE_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Shell:"
	@ls -lh $(SHELL_UTILS) 2>/dev/null || true
	@echo ""
	@echo ""
	@echo "Text display/formatting utilities:"
	@ls -lh $(DISPLAY_UTILS) 2>/dev/null || true
	@echo ""
	@ls -lh $(STRING_UTILS) 2>/dev/null || true
	@echo "POSIX compliance utilities:"
	@ls -lh $(POSIX_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Terminal and I/O utilities:"
	@ls -lh $(TERMINAL_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Networking utilities:"
	@ls -lh $(NET_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Kernel utilities:"
	@ls -lh $(KERNEL_UTILS) 2>/dev/null || true
	@echo ""
	@echo "System control utilities:"
	@ls -lh $(SYSTEM_UTILS) 2>/dev/null || true
	@echo ""
	@echo "Boot utilities (init system):"
	@ls -lh $(BOOT_UTILS) 2>/dev/null || true

# Build system control utilities
.PHONY: system-utils
system-utils: $(SYSTEM_UTILS)
	@echo "✓ System control utilities built!"
	@ls -lh $(SYSTEM_UTILS) 2>/dev/null || true

# Build boot utilities (essential for bootable system)
.PHONY: boot-utils
boot-utils: $(BOOT_UTILS)
	@echo "✓ Boot utilities built!"
	@ls -lh $(BOOT_UTILS) 2>/dev/null || true

# Build file utilities
.PHONY: file-utils
file-utils: $(FILE_UTILS)
	@echo "✓ File utilities built!"

# Build text utilities
.PHONY: text-utils
text-utils: $(TEXT_UTILS)
	@echo "✓ Text utilities built!"

# Build advanced text utilities
.PHONY: advanced-text-utils
advanced-text-utils: $(ADVANCED_TEXT_UTILS)
	@echo "✓ Advanced text utilities built!"
	@ls -lh $(ADVANCED_TEXT_UTILS) 2>/dev/null || true

# Build string/formatting utilities
.PHONY: string-utils
string-utils: $(STRING_UTILS)

# Build text display/formatting utilities
.PHONY: display-utils
display-utils: $(DISPLAY_UTILS)
	@echo "✓ Text display/formatting utilities built!"
	@ls -lh $(DISPLAY_UTILS) 2>/dev/null || true

# Build system info utilities
.PHONY: sysinfo-utils
sysinfo-utils: $(SYSINFO_UTILS)
	@echo "✓ System info utilities built!"

# Build process utilities
.PHONY: proc-utils
proc-utils: $(PROC_UTILS)
	@echo "✓ Process utilities built!"

# Build disk utilities
.PHONY: disk-utils
disk-utils: $(DISK_UTILS)
	@echo "✓ Disk utilities built!"

# Build search utilities
.PHONY: search-utils
search-utils: $(SEARCH_UTILS)
	@echo "✓ Search utilities built!"

# Build time and permission utilities
.PHONY: time-perm-utils
time-perm-utils: $(TIME_PERM_UTILS)
	@echo "✓ Time and permission utilities built!"

# Build shell scripting utilities
.PHONY: shell-utils
shell-utils: $(SHELL_SCRIPT_UTILS)
	@echo "✓ Shell scripting utilities built!"
	@ls -lh $(SHELL_SCRIPT_UTILS) 2>/dev/null || true

# Build math utilities
.PHONY: math-utils
math-utils: $(MATH_UTILS)
	@echo "✓ Math utilities built!"
	@ls -lh $(MATH_UTILS) 2>/dev/null || true

# Build archive utilities
.PHONY: archive-utils
archive-utils: $(ARCHIVE_UTILS)
	@echo "✓ Archive utilities built!"
	@ls -lh $(ARCHIVE_UTILS) 2>/dev/null || true

# Build diff/comparison utilities
.PHONY: diff-utils
diff-utils: $(DIFF_UTILS)
	@echo "✓ Diff/comparison utilities built!"
	@ls -lh $(DIFF_UTILS) 2>/dev/null || true

# Build POSIX utilities
.PHONY: posix-utils
posix-utils: $(POSIX_UTILS)
	@echo "✓ POSIX compliance utilities built!"
	@ls -lh $(POSIX_UTILS) 2>/dev/null || true

# Build terminal utilities
.PHONY: terminal-utils
terminal-utils: $(TERMINAL_UTILS)
	@echo "✓ Terminal and I/O utilities built!"
	@ls -lh $(TERMINAL_UTILS) 2>/dev/null || true

# Build networking utilities
.PHONY: net-utils
net-utils: $(NET_UTILS)
	@echo "✓ Networking utilities built!"
	@ls -lh $(NET_UTILS) 2>/dev/null || true

# Build kernel utilities
.PHONY: kernel-utils
kernel-utils: $(KERNEL_UTILS)
	@echo "✓ Kernel utilities built!"
	@ls -lh $(KERNEL_UTILS) 2>/dev/null || true

# Graphics utilities target
.PHONY: graphics
graphics: $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/pixel $(BIN_DIR)/line $(BIN_DIR)/rect $(BIN_DIR)/circle
	@echo "✓ Graphics utilities built!"
	@ls -lh $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/pixel $(BIN_DIR)/line $(BIN_DIR)/rect $(BIN_DIR)/circle

# Graphical applications target (desktop environment)
.PHONY: graphical-apps
graphical-apps: $(GRAPHICAL_APPS)
	@echo "✓ Graphical applications built!"
	@echo ""
	@echo "Desktop Environment:"
	@ls -lh $(GRAPHICAL_APPS) 2>/dev/null || true
	@echo ""
	@echo "Run 'sudo ./bin/bds' to start the desktop environment"

# Test graphics utilities
.PHONY: test-graphics
test-graphics: $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/demo
	@echo "Running graphics test suite..."
	@./test_graphics.sh

# Quick framebuffer info (safe to run in X11)
.PHONY: test-graphics-info
test-graphics-info: $(BIN_DIR)/fbinfo
	@echo "Querying framebuffer (requires /dev/fb0 access)..."
	@sudo chown $$USER /dev/fb0 2>/dev/null || true
	@./$(BIN_DIR)/fbinfo || echo "Run: sudo chown $$USER /dev/fb0"

# Test echo utility
.PHONY: test-echo
test-echo: $(BIN_DIR)/echo
	@echo "Testing echo utility..."
	@echo "========================================"
	@./$(BIN_DIR)/echo
	@echo "========================================"
	@echo "✓ Echo test complete!"

# Clean userland binaries
.PHONY: clean-userland
clean-userland:
	@echo "Cleaning userland binaries..."
	@rm -rf $(BIN_DIR)
	@rm -f $(LIB_DIR)/syscalls.o

# ========== DEBUGGING TARGETS ==========

# Disassemble bootloader (for debugging)
.PHONY: disasm-boot
disasm-boot: $(STAGE1_BIN) $(STAGE2_BIN)
	@echo "=== Stage 1 Disassembly ==="
	ndisasm -b 16 $(STAGE1_BIN) | head -30
	@echo ""
	@echo "=== Stage 2 Disassembly ==="
	ndisasm -b 16 $(STAGE2_BIN) | head -50

# Disassemble kernel
.PHONY: disasm-kernel
disasm-kernel: $(KERNEL_BIN)
	objdump -D -M intel $(KERNEL_BIN) | less

# Display help
.PHONY: help
help:
	@echo "BrainhairOS Build System"
	@echo "========================="
	@echo ""
	@echo "Primary Targets:"
	@echo "  all            - Build bootable disk image with custom bootloader"
	@echo "  grub           - Build GRUB multiboot ISO (RECOMMENDED)"
	@echo "  run            - Boot custom bootloader in QEMU"
	@echo "  run-grub       - Boot with GRUB (fast, recommended)"
	@echo "  run-grub-iso   - Boot GRUB ISO in QEMU"
	@echo ""
	@echo "Build Targets:"
	@echo "  kernel         - Build kernel only"
	@echo "  bootloader     - Build custom bootloader only"
	@echo "  brainhair        - Build with Brainhair kernel"
	@echo ""
	@echo "Debug Targets:"
	@echo "  run-debug      - Boot in QEMU with debug output"
	@echo "  debug          - Start QEMU with GDB server"
	@echo "  disasm-boot    - Disassemble bootloader"
	@echo "  disasm-kernel  - Disassemble kernel"
	@echo ""
	@echo "Utility:"
	@echo "  clean          - Remove build artifacts"
	@echo "  check-tools    - Verify required tools"
	@echo "  help           - Show this help"
	@echo ""
	@echo "Quick start (GRUB - recommended):"
	@echo "  make check-tools    # Verify tools"
	@echo "  make run-grub       # Build and boot with GRUB"
	@echo ""
	@echo "Quick start (custom bootloader):"
	@echo "  make check-tools    # Verify tools"
	@echo "  make                # Build disk image"
	@echo "  make run            # Boot it!"

# =============================================================================
# Distribution Targets
# =============================================================================

.PHONY: distro rootfs initramfs test-qemu

# Create root filesystem
rootfs:
	@echo "Creating BrainhairOS root filesystem..."
	@./distro/scripts/create_rootfs.sh

# Create initramfs
initramfs: userland
	@echo "Creating BrainhairOS initramfs..."
	@./distro/scripts/create_disk_image.sh

# Test with QEMU (serial console)
test-qemu: initramfs
	@echo "Starting BrainhairOS in QEMU..."
	qemu-system-x86_64 -m 256M \
		-kernel /boot/vmlinuz-$$(uname -r) \
		-initrd distro/brainhair-full.cpio.gz \
		-append 'console=ttyS0 rdinit=/init' \
		-nographic

# Test with QEMU (graphical)
test-qemu-gui: initramfs
	@echo "Starting BrainhairOS in QEMU (GUI)..."
	qemu-system-x86_64 -m 256M \
		-kernel /boot/vmlinuz-$$(uname -r) \
		-initrd distro/brainhair-full.cpio.gz \
		-append 'console=tty0 rdinit=/init'

# Full distro build
distro: userland rootfs initramfs
	@echo ""
	@echo "=== BrainhairOS Distribution Built ==="
	@echo "Root filesystem: distro/rootfs/"
	@echo "Initramfs: distro/brainhair-full.cpio.gz"
	@echo ""
	@echo "Test with: make test-qemu"

# =============================================================================
# Test Targets
# =============================================================================

.PHONY: test test-quick test-userland test-kernel test-http

# Run full test suite
test:
	@echo "Running BrainhairOS test suite..."
	@./tests/run_tests.sh

# Run quick tests (no QEMU)
test-quick:
	@echo "Running quick tests..."
	@./tests/run_tests.sh --quick

# Test userland utilities only
test-userland:
	@echo "Testing userland utilities..."
	@./tests/test_userland.sh

# Test kernel boot
test-kernel: microkernel-uweb
	@echo "Testing kernel boot..."
	@./tests/test_kernel.sh

# Test HTTP server
test-http: microkernel-uweb
	@echo "Testing HTTP server..."
	@./tests/test_http.sh
