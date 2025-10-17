/*
 * kernel_support.h - Support functions for Nim kernel
 */

#ifndef KERNEL_SUPPORT_H
#define KERNEL_SUPPORT_H

#include <stdint.h>

// Port I/O
static inline uint8_t inb_nim(uint16_t port) {
    uint8_t value;
    __asm__ volatile ("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

static inline void outb_nim(uint16_t port, uint8_t value) {
    __asm__ volatile ("outb %0, %1" : : "a"(value), "Nd"(port));
}

static inline void hlt_nim(void) {
    __asm__ volatile ("hlt");
}

#endif
