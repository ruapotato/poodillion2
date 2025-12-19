/*
 * keyboard.c - PS/2 Keyboard Driver for BrainhairOS
 *
 * Simple PS/2 keyboard driver using polling (no interrupts yet)
 */

#include <stdint.h>
#include <stddef.h>
#include "keyboard.h"

// PS/2 Keyboard ports
#define KBD_DATA_PORT    0x60
#define KBD_STATUS_PORT  0x64

// Scancode to ASCII table (US keyboard layout, scancode set 1)
static const char scancode_to_ascii[128] = {
    0,  27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b',
    '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',
    0,    'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`',
    0,    '\\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 0,
    '*',  0,    ' '
};

// Shifted scancode table
static const char scancode_to_ascii_shift[128] = {
    0,  27, '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '\b',
    '\t', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '\n',
    0,    'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~',
    0,    '|', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', 0,
    '*',  0,    ' '
};

// Keyboard state
static uint8_t shift_pressed = 0;
static uint8_t ctrl_pressed = 0;

// Read byte from port
static inline uint8_t inb(uint16_t port) {
    uint8_t value;
    __asm__ volatile ("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

// Write byte to port
static inline void outb(uint16_t port, uint8_t value) {
    __asm__ volatile ("outb %0, %1" : : "a"(value), "Nd"(port));
}

void keyboard_init(void) {
    // For now, just clear any pending data
    while (inb(KBD_STATUS_PORT) & 0x01) {
        inb(KBD_DATA_PORT);
    }
}

int keyboard_available(void) {
    // Check if data is available in keyboard buffer
    return (inb(KBD_STATUS_PORT) & 0x01);
}

char keyboard_getchar(void) {
    uint8_t scancode;
    char ascii;

    // Wait for key press
    while (!keyboard_available()) {
        __asm__ volatile ("pause");
    }

    scancode = inb(KBD_DATA_PORT);

    // Handle key release (scancode has high bit set)
    if (scancode & 0x80) {
        // Key release
        scancode &= 0x7F;

        // Update modifier state
        if (scancode == 0x2A || scancode == 0x36) {  // Left/Right Shift
            shift_pressed = 0;
        } else if (scancode == 0x1D) {  // Ctrl
            ctrl_pressed = 0;
        }

        return 0;  // No character for key release
    }

    // Handle key press
    // Update modifier state
    if (scancode == 0x2A || scancode == 0x36) {  // Left/Right Shift
        shift_pressed = 1;
        return 0;
    } else if (scancode == 0x1D) {  // Ctrl
        ctrl_pressed = 1;
        return 0;
    }

    // Convert scancode to ASCII
    if (scancode < 128) {
        if (shift_pressed) {
            ascii = scancode_to_ascii_shift[scancode];
        } else {
            ascii = scancode_to_ascii[scancode];
        }

        // Handle Ctrl combinations
        if (ctrl_pressed && ascii >= 'a' && ascii <= 'z') {
            ascii = ascii - 'a' + 1;  // Ctrl+A = 1, Ctrl+B = 2, etc.
        } else if (ctrl_pressed && ascii >= 'A' && ascii <= 'Z') {
            ascii = ascii - 'A' + 1;
        }

        return ascii;
    }

    return 0;
}

int keyboard_shift_pressed(void) {
    return shift_pressed;
}

int keyboard_ctrl_pressed(void) {
    return ctrl_pressed;
}
