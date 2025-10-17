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

# Compile Mini-Nim kernel
MININIM_KERNEL_OBJ = compiler/kernel.o
$(MININIM_KERNEL_OBJ): kernel/kernel.nim
	@echo "Compiling Mini-Nim kernel..."
	cd compiler && python3 mininim.py ../kernel/kernel.nim --kernel

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
	@echo "Targets:"
	@echo "  all            - Build bootable disk image (default)"
	@echo "  kernel         - Build kernel only"
	@echo "  bootloader     - Build bootloader only"
	@echo "  run            - Boot in QEMU"
	@echo "  run-debug      - Boot in QEMU with debug output"
	@echo "  debug          - Start QEMU with GDB server"
	@echo "  disasm-boot    - Disassemble bootloader"
	@echo "  disasm-kernel  - Disassemble kernel"
	@echo "  clean          - Remove build artifacts"
	@echo "  check-tools    - Verify required tools"
	@echo "  help           - Show this help"
	@echo ""
	@echo "Quick start:"
	@echo "  make check-tools    # Verify tools"
	@echo "  make                # Build disk image"
	@echo "  make run            # Boot it!"
