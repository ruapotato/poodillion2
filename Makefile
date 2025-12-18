# Makefile for PoodillionOS
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
DISK_IMG = $(BUILD_DIR)/poodillion.img

# Source files
STAGE1_ASM = $(BOOT_DIR)/stage1.asm
STAGE2_ASM = $(BOOT_DIR)/stage2.asm
BOOT_ASM = $(BOOT_DIR)/boot.asm
KERNEL_C = $(KERNEL_DIR)/kernel.c
KERNEL_NIM = $(NIM_DIR)/kernel.nim

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

# Compile Mini-Nim kernel (for custom bootloader - deprecated)
MININIM_KERNEL_OBJ = compiler/kernel.o
$(MININIM_KERNEL_OBJ): kernel/kernel.nim
	@echo "Compiling Mini-Nim kernel..."
	cd compiler && python3 mininim.py ../kernel/kernel.nim --kernel

# Compile Mini-Nim kernel for GRUB
MININIM_KERNEL_OBJ_GRUB = $(BUILD_DIR)/kernel_mininim.o
SERIAL_OBJ = $(BUILD_DIR)/serial.o
MININIM_WRAPPER_OBJ = $(BUILD_DIR)/mininim_wrapper.o

$(MININIM_KERNEL_OBJ_GRUB): kernel/kernel.nim | $(BUILD_DIR)
	@echo "Compiling Mini-Nim kernel for GRUB..."
	cd compiler && python3 mininim.py ../kernel/kernel.nim --kernel -o kernel_mininim
	@mv compiler/kernel_mininim.o $(MININIM_KERNEL_OBJ_GRUB)
	@echo "  Mini-Nim kernel compiled: $(MININIM_KERNEL_OBJ_GRUB)"

$(SERIAL_OBJ): kernel/serial.asm | $(BUILD_DIR)
	@echo "Assembling serial driver..."
	$(AS) $(ASFLAGS_32) kernel/serial.asm -o $(SERIAL_OBJ)

$(MININIM_WRAPPER_OBJ): kernel/mininim_wrapper.asm | $(BUILD_DIR)
	@echo "Assembling Mini-Nim wrapper..."
	$(AS) $(ASFLAGS_32) kernel/mininim_wrapper.asm -o $(MININIM_WRAPPER_OBJ)

# Build kernel with Mini-Nim compiler
.PHONY: kernel-mininim
kernel-mininim: $(BOOT_OBJ) $(MININIM_KERNEL_OBJ)
	@echo "Linking Mini-Nim kernel..."
	$(LD) $(LDFLAGS) -o $(BUILD_DIR)/kernel.elf $(BOOT_OBJ) $(MININIM_KERNEL_OBJ)
	@echo "Converting ELF to flat binary..."
	objcopy -O binary $(BUILD_DIR)/kernel.elf $(KERNEL_BIN)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_BIN)) bytes"

# Compile Nim kernel
.PHONY: kernel-nim
kernel-nim: $(BUILD_DIR)
	@echo "Compiling Nim kernel..."
	cd $(NIM_DIR) && $(NIM) c --nimcache:../$(BUILD_DIR)/nimcache -c kernel.nim
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

# Build full disk image with Mini-Nim kernel
.PHONY: mininim
mininim: $(STAGE1_BIN) $(STAGE2_BIN) kernel-mininim
	@echo "Creating disk image with Mini-Nim kernel..."
	dd if=/dev/zero of=$(DISK_IMG) bs=512 count=20480 2>/dev/null
	dd if=$(STAGE1_BIN) of=$(DISK_IMG) conv=notrunc bs=512 count=1 2>/dev/null
	dd if=$(STAGE2_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=1 2>/dev/null
	dd if=$(KERNEL_BIN) of=$(DISK_IMG) conv=notrunc bs=512 seek=18 2>/dev/null
	@echo "✓ Mini-Nim disk image created: $(DISK_IMG)"
	@echo "  Kernel: Mini-Nim compiled!"
	@echo "  Run with: make run"

# Build just the kernel
.PHONY: kernel
kernel: $(KERNEL_BIN)

# Build bootloader only
.PHONY: bootloader
bootloader: $(STAGE1_BIN) $(STAGE2_BIN)

# Run in QEMU
.PHONY: run
run: $(DISK_IMG)
	@echo "Booting PoodillionOS in QEMU..."
	qemu-system-i386 -drive file=$(DISK_IMG),format=raw

# Run with debugging output
.PHONY: run-debug
run-debug: $(DISK_IMG)
	@echo "Booting PoodillionOS in QEMU (debug mode)..."
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
GRUB_ISO = $(BUILD_DIR)/poodillion_grub.iso

# Build multiboot kernel for GRUB (C version)
$(KERNEL_ELF): $(MULTIBOOT_OBJ) $(KERNEL_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building multiboot kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_ELF) $(MULTIBOOT_OBJ) $(KERNEL_OBJ)
	@echo "  Kernel size: $$(stat -c%s $(KERNEL_ELF)) bytes"

# Build Mini-Nim multiboot kernel for GRUB
KERNEL_MININIM_ELF = $(ISO_DIR)/boot/kernel_mininim.elf
$(KERNEL_MININIM_ELF): $(MULTIBOOT_OBJ) $(MININIM_KERNEL_OBJ_GRUB) $(SERIAL_OBJ) $(MININIM_WRAPPER_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building Mini-Nim multiboot kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_MININIM_ELF) $(MULTIBOOT_OBJ) $(MININIM_WRAPPER_OBJ) $(SERIAL_OBJ) $(MININIM_KERNEL_OBJ_GRUB)
	@echo "  Mini-Nim Kernel size: $$(stat -c%s $(KERNEL_MININIM_ELF)) bytes"

$(MULTIBOOT_OBJ): $(MULTIBOOT_ASM) | $(BUILD_DIR)
	@echo "Assembling multiboot header..."
	$(AS) $(ASFLAGS_32) $(MULTIBOOT_ASM) -o $(MULTIBOOT_OBJ)

$(GRUB_DIR):
	@mkdir -p $(GRUB_DIR)
	@echo "set timeout=0" > $(GRUB_DIR)/grub.cfg
	@echo "set default=0" >> $(GRUB_DIR)/grub.cfg
	@echo "" >> $(GRUB_DIR)/grub.cfg
	@echo 'menuentry "PoodillionOS" {' >> $(GRUB_DIR)/grub.cfg
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
	@echo "Booting PoodillionOS with GRUB (multiboot)..."
	@echo "Serial output below (Ctrl-C to exit):"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_ELF) -display none -serial stdio

# Mini-Nim kernel targets
.PHONY: grub-mininim
grub-mininim: $(KERNEL_MININIM_ELF)
	@echo "✓ Mini-Nim kernel ready!"
	@echo "  Boot with: make run-grub-mininim"

.PHONY: run-grub-mininim
run-grub-mininim: $(KERNEL_MININIM_ELF)
	@echo "Booting PoodillionOS Mini-Nim Kernel with GRUB..."
	@echo "Serial output below (Ctrl-C to exit):"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_MININIM_ELF) -display none -serial stdio

.PHONY: run-grub-mininim-gui
run-grub-mininim-gui: $(KERNEL_MININIM_ELF)
	@echo "Booting PoodillionOS Mini-Nim Kernel with GRUB (GUI)..."
	qemu-system-i386 -kernel $(KERNEL_MININIM_ELF)

# Interactive Shell kernel targets
KEYBOARD_OBJ = $(BUILD_DIR)/keyboard.o
VGA_OBJ = $(BUILD_DIR)/vga.o
SHELL_OBJ = $(BUILD_DIR)/shell.o
SHELL_WRAPPER_OBJ = $(BUILD_DIR)/shell_wrapper.o
KERNEL_SHELL_ELF = $(ISO_DIR)/boot/kernel_shell.elf

$(KEYBOARD_OBJ): kernel/keyboard.asm | $(BUILD_DIR)
	@echo "Assembling keyboard driver..."
	$(AS) $(ASFLAGS_32) kernel/keyboard.asm -o $(KEYBOARD_OBJ)

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
	@echo "Booting PoodillionOS Interactive Shell..."
	@echo "========================================"
	@echo "Type commands and press Enter."
	@echo "Try: help, clear, echo, ls, ps, uname"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_SHELL_ELF)

.PHONY: run-shell-serial
run-shell-serial: $(KERNEL_SHELL_ELF)
	@echo "Booting PoodillionOS Interactive Shell (with serial)..."
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
	@echo "Booting PoodillionOS Serial Shell..."
	@echo "Serial output below (Ctrl-C to exit):"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_SERIAL_SHELL_ELF) -display none -serial stdio

# Mini-Nim Shell kernel targets (VGA-based, kept for reference)
MININIM_SHELL_OBJ = $(BUILD_DIR)/shell_mininim.o
MININIM_SHELL_WRAPPER_OBJ = $(BUILD_DIR)/mininim_shell_wrapper.o
KERNEL_MININIM_SHELL_ELF = $(ISO_DIR)/boot/kernel_mininim_shell.elf

$(MININIM_SHELL_OBJ): kernel/shell_mininim.nim | $(BUILD_DIR)
	@echo "Compiling Mini-Nim shell kernel..."
	cd compiler && python3 mininim.py ../kernel/shell_mininim.nim --kernel -o shell_mininim
	@mv compiler/shell_mininim.o $(MININIM_SHELL_OBJ)
	@echo "  Mini-Nim shell compiled: $(MININIM_SHELL_OBJ)"

$(MININIM_SHELL_WRAPPER_OBJ): kernel/mininim_shell_wrapper.asm | $(BUILD_DIR)
	@echo "Assembling Mini-Nim shell wrapper..."
	$(AS) $(ASFLAGS_32) kernel/mininim_shell_wrapper.asm -o $(MININIM_SHELL_WRAPPER_OBJ)

$(KERNEL_MININIM_SHELL_ELF): $(MULTIBOOT_OBJ) $(SERIAL_OBJ) $(MININIM_SHELL_WRAPPER_OBJ) $(MININIM_SHELL_OBJ) $(LINKER_GRUB) | $(GRUB_DIR)
	@echo "Building Mini-Nim shell kernel for GRUB..."
	$(LD) -m elf_i386 -T $(LINKER_GRUB) -o $(KERNEL_MININIM_SHELL_ELF) $(MULTIBOOT_OBJ) $(MININIM_SHELL_WRAPPER_OBJ) $(SERIAL_OBJ) $(MININIM_SHELL_OBJ)
	@echo "  Mini-Nim Shell Kernel size: $$(stat -c%s $(KERNEL_MININIM_SHELL_ELF)) bytes"

.PHONY: mininim-shell
mininim-shell: $(KERNEL_MININIM_SHELL_ELF)
	@echo "✓ Mini-Nim shell kernel ready!"
	@echo "  Boot with: make run-mininim-shell"

.PHONY: run-mininim-shell
run-mininim-shell: $(KERNEL_MININIM_SHELL_ELF)
	@echo "Booting PoodillionOS Mini-Nim Shell (VGA)..."
	@echo "========================================"
	@echo "Shell written in Mini-Nim!"
	@echo "Commands: ls, cat, echo, help"
	@echo "========================================"
	qemu-system-i386 -kernel $(KERNEL_MININIM_SHELL_ELF)

# NEW: Full Mini-Nim Shell with extern functions (SERIAL OUTPUT)
.PHONY: run-nim-shell
run-nim-shell: build/kernel_shell_nim.elf
	@echo "========================================"
	@echo "  PoodillionOS v0.1 - Mini-Nim Shell"
	@echo "========================================"
	@echo "Full OS shell written in Mini-Nim!"
	@echo "Commands: ls, cat, echo, help"
	@echo "Press Ctrl-C to exit"
	@echo "========================================"
	qemu-system-i386 -kernel build/kernel_shell_nim.elf -serial stdio -display none

# Build Mini-Nim shell kernel
build/kernel_shell_nim.elf: compiler/shell_nim.o build/multiboot.o build/serial.o kernel/mininim_shell_wrapper.asm | $(BUILD_DIR)
	@echo "Building Mini-Nim shell kernel..."
	@nasm -f elf32 kernel/mininim_shell_wrapper.asm -o build/wrapper_shell.o
	@ld -m elf_i386 -T boot/linker_grub.ld -o build/kernel_shell_nim.elf build/multiboot.o build/wrapper_shell.o build/serial.o compiler/shell_nim.o
	@echo "  Mini-Nim Shell Kernel: $$(stat -c%s build/kernel_shell_nim.elf) bytes"

compiler/shell_nim.o: kernel/shell_nim.nim
	@echo "Compiling Mini-Nim shell..."
	cd compiler && python3 mininim.py ../kernel/shell_nim.nim --kernel -o shell_nim
	@echo "  Shell compiled: $$(stat -c%s compiler/shell_nim.o) bytes"

.PHONY: run-grub-iso
run-grub-iso: $(GRUB_ISO)
	@echo "Booting PoodillionOS from GRUB ISO..."
	qemu-system-i386 -cdrom $(GRUB_ISO)

# ========== USER LAND UTILITIES ==========

# Userland directories
USERLAND_DIR = userland
LIB_DIR = lib
BIN_DIR = bin

# Create bin directory
$(BIN_DIR):
	@mkdir -p $(BIN_DIR)

# Build syscall library
$(LIB_DIR)/syscalls.o: $(LIB_DIR)/syscalls.asm | $(BUILD_DIR)
	@echo "Assembling syscall library..."
	$(AS) $(ASFLAGS_32) $(LIB_DIR)/syscalls.asm -o $(LIB_DIR)/syscalls.o

# Generic rule to compile userland utilities
$(BIN_DIR)/%: $(USERLAND_DIR)/%.nim $(LIB_DIR)/syscalls.o | $(BIN_DIR)
	@echo "Compiling $* utility..."
	cd compiler && python3 mininim.py ../$(USERLAND_DIR)/$*.nim --asm-only > $*.asm
	@echo "Assembling $* utility..."
	$(AS) $(ASFLAGS_32) compiler/$*.asm -o compiler/$*.o
	@echo "Linking $* utility..."
	$(LD) -m elf_i386 -o $(BIN_DIR)/$* compiler/$*.o $(LIB_DIR)/syscalls.o
	@echo "  Created: $(BIN_DIR)/$* ($$(stat -c%s $(BIN_DIR)/$*) bytes)"
	@rm -f compiler/$*.o compiler/$*.asm

# Core utilities (original)
CORE_UTILS = $(BIN_DIR)/echo $(BIN_DIR)/true $(BIN_DIR)/false $(BIN_DIR)/cat $(BIN_DIR)/edit

# Data pipeline utilities
DATA_UTILS = $(BIN_DIR)/ps $(BIN_DIR)/inspect $(BIN_DIR)/where $(BIN_DIR)/count $(BIN_DIR)/head $(BIN_DIR)/tail $(BIN_DIR)/select $(BIN_DIR)/sort $(BIN_DIR)/fmt $(BIN_DIR)/ls

# Graphics utilities
GRAPHICS_UTILS = $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/demo $(BIN_DIR)/pixel $(BIN_DIR)/line $(BIN_DIR)/rect $(BIN_DIR)/circle

# File manipulation utilities (new)
FILE_UTILS = $(BIN_DIR)/rm $(BIN_DIR)/mkdir $(BIN_DIR)/rmdir $(BIN_DIR)/mv $(BIN_DIR)/touch $(BIN_DIR)/cp

# Text processing utilities (new)
TEXT_UTILS = $(BIN_DIR)/wc $(BIN_DIR)/tee $(BIN_DIR)/rev $(BIN_DIR)/yes $(BIN_DIR)/seq $(BIN_DIR)/cut $(BIN_DIR)/uniq $(BIN_DIR)/tr $(BIN_DIR)/basename $(BIN_DIR)/dirname

# System info utilities (new)
SYSINFO_UTILS = $(BIN_DIR)/uname $(BIN_DIR)/free $(BIN_DIR)/uptime $(BIN_DIR)/hostname $(BIN_DIR)/whoami $(BIN_DIR)/id

# Process utilities (new)
PROC_UTILS = $(BIN_DIR)/kill $(BIN_DIR)/pidof $(BIN_DIR)/sleep

# Disk utilities (new)
DISK_UTILS = $(BIN_DIR)/df $(BIN_DIR)/du $(BIN_DIR)/stat $(BIN_DIR)/file $(BIN_DIR)/ln $(BIN_DIR)/readlink

# File search utilities
SEARCH_UTILS = $(BIN_DIR)/find $(BIN_DIR)/od $(BIN_DIR)/strings

# Time and permission utilities
TIME_PERM_UTILS = $(BIN_DIR)/date $(BIN_DIR)/chmod $(BIN_DIR)/chown $(BIN_DIR)/chgrp $(BIN_DIR)/pwd

# Shell scripting utilities
SHELL_SCRIPT_UTILS = $(BIN_DIR)/test $(BIN_DIR)/expr $(BIN_DIR)/which $(BIN_DIR)/xargs $(BIN_DIR)/env

# Shell
SHELL_UTILS = $(BIN_DIR)/psh

# All utilities
ALL_UTILS = $(CORE_UTILS) $(DATA_UTILS) $(GRAPHICS_UTILS) $(FILE_UTILS) $(TEXT_UTILS) $(SYSINFO_UTILS) $(PROC_UTILS) $(DISK_UTILS) $(SEARCH_UTILS) $(TIME_PERM_UTILS) $(SHELL_SCRIPT_UTILS) $(SHELL_UTILS)

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
	@echo "Shell:"
	@ls -lh $(SHELL_UTILS) 2>/dev/null || true

# Build file utilities
.PHONY: file-utils
file-utils: $(FILE_UTILS)
	@echo "✓ File utilities built!"

# Build text utilities
.PHONY: text-utils
text-utils: $(TEXT_UTILS)
	@echo "✓ Text utilities built!"

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

# Graphics utilities target
.PHONY: graphics
graphics: $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/pixel $(BIN_DIR)/line $(BIN_DIR)/rect $(BIN_DIR)/circle
	@echo "✓ Graphics utilities built!"
	@ls -lh $(BIN_DIR)/fbinfo $(BIN_DIR)/clear $(BIN_DIR)/pixel $(BIN_DIR)/line $(BIN_DIR)/rect $(BIN_DIR)/circle

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
	@echo "PoodillionOS Build System"
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
	@echo "  mininim        - Build with Mini-Nim kernel"
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
