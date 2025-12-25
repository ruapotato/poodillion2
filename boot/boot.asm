; boot.asm - BrainhairOS Kernel Entry Point
; For custom bootloader (no multiboot needed)

[BITS 32]

section .text
global _start
extern brainhair_kernel_main

_start:
    ; Set up stack (at 640KB, just before VGA memory)
    mov esp, 0x90000

    ; Call kernel main
    call brainhair_kernel_main

    ; Hang if kernel returns
.hang:
    cli         ; Disable interrupts
    hlt         ; Halt CPU
    jmp .hang   ; Loop forever
