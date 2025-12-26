; boot.asm - BrainhairOS Kernel Entry Point
; For custom bootloader (no multiboot needed)

[BITS 32]

section .text
global _start
extern brainhair_kernel_main
extern _bss_start
extern _bss_end

_start:
    ; Set up stack (at 640KB, just before VGA memory)
    mov esp, 0x90000

    ; Zero the BSS section
    cld                     ; Clear direction flag (forward)
    mov edi, _bss_start
    mov ecx, _bss_end
    sub ecx, edi            ; ECX = BSS size in bytes
    shr ecx, 2              ; ECX = number of dwords
    xor eax, eax            ; Zero value
    rep stosd               ; Zero BSS

    ; Call kernel main
    call brainhair_kernel_main

    ; Hang if kernel returns
.hang:
    cli         ; Disable interrupts
    hlt         ; Halt CPU
    jmp .hang   ; Loop forever
