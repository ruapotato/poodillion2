// Simple C kernel to demonstrate working bootloader
#include <stdint.h>

// Serial port (COM1) base address
#define SERIAL_PORT 0x3F8

// Initialize serial port
static void serial_init(void) {
    __asm__ volatile(
        "mov $0x00, %%al\n"
        "mov $0x3F9, %%dx\n"
        "out %%al, %%dx\n"      // Disable interrupts
        "mov $0x80, %%al\n"
        "mov $0x3FB, %%dx\n"
        "out %%al, %%dx\n"      // Enable DLAB
        "mov $0x03, %%al\n"
        "mov $0x3F8, %%dx\n"
        "out %%al, %%dx\n"      // Set divisor low byte (38400 baud)
        "mov $0x00, %%al\n"
        "mov $0x3F9, %%dx\n"
        "out %%al, %%dx\n"      // Set divisor high byte
        "mov $0x03, %%al\n"
        "mov $0x3FB, %%dx\n"
        "out %%al, %%dx\n"      // 8 bits, no parity, one stop bit
        "mov $0xC7, %%al\n"
        "mov $0x3FA, %%dx\n"
        "out %%al, %%dx\n"      // Enable FIFO
        "mov $0x0B, %%al\n"
        "mov $0x3FC, %%dx\n"
        "out %%al, %%dx\n"      // IRQs enabled, RTS/DSR set
        ::: "al", "dx"
    );
}

// Write character to serial port
static void serial_write(char c) {
    // Wait for transmit buffer to be empty
    while (1) {
        uint8_t status;
        __asm__ volatile(
            "mov $0x3FD, %%dx\n"
            "in %%dx, %%al\n"
            : "=a"(status)
            :: "dx"
        );
        if (status & 0x20) break;
    }

    // Write character
    __asm__ volatile(
        "mov $0x3F8, %%dx\n"
        "out %%al, %%dx\n"
        :: "a"(c), "d"(SERIAL_PORT)
    );
}

// Write string to serial port
static void serial_print(const char* str) {
    while (*str) {
        serial_write(*str++);
    }
}

void kernel_main(void) {
    // Initialize serial port
    serial_init();

    // Print to serial (visible with -nographic or -serial stdio)
    serial_print("\n\n");
    serial_print("========================================\n");
    serial_print("  BrainhairOS Kernel Booted!\n");
    serial_print("========================================\n");
    serial_print("\n");
    serial_print("Status: GRUB multiboot successful!\n");
    serial_print("Bootloader: GRUB handled protected mode\n");
    serial_print("Kernel: Loaded at 0x100000 (1MB)\n");
    serial_print("\n");
    serial_print("VGA output (see GUI window):\n");

    // Also write to VGA for GUI display
    uint16_t* vga = (uint16_t*)0xB8000;
    const char* msg = "BOOTLOADER WORKS! Brainhair coming soon...";
    uint8_t color = 0x0A; // Green on black

    for (int i = 0; msg[i] != '\0'; i++) {
        vga[i] = (uint16_t)msg[i] | (uint16_t)(color << 8);
    }

    serial_print("  \"BOOTLOADER WORKS! Brainhair coming soon...\"\n");
    serial_print("\n");
    serial_print("Next: Implement Brainhair compiler backend!\n");
    serial_print("\n");
    serial_print("Kernel halted. Press Ctrl-A X to exit QEMU.\n");

    // Halt
    while(1) {
        __asm__("hlt");
    }
}
