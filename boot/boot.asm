; boot.asm - PoodillionOS Bootloader
; Multiboot2 header for GRUB

section .multiboot
align 4
multiboot_start:
    dd 0xe85250d6                ; magic number (multiboot2)
    dd 0                         ; architecture 0 (i386)
    dd multiboot_end - multiboot_start  ; header length
    ; checksum
    dd -(0xe85250d6 + 0 + (multiboot_end - multiboot_start))

    ; End tag
    dw 0    ; type
    dw 0    ; flags
    dd 8    ; size
multiboot_end:

section .bss
align 16
stack_bottom:
    resb 16384  ; 16 KB stack
stack_top:

section .text
global _start
extern main

_start:
    ; Set up stack
    mov esp, stack_top

    ; Call kernel main
    call main

    ; Hang if kernel returns
.hang:
    cli         ; Disable interrupts
    hlt         ; Halt CPU
    jmp .hang   ; Loop forever
