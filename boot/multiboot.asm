; Multiboot header for GRUB
; GRUB will handle protected mode transition for us!

section .multiboot
align 4
    ; Multiboot magic number
    dd 0x1BADB002

    ; Flags: align modules on page boundaries, provide memory map
    dd 0x00000003

    ; Checksum (must be: -(magic + flags))
    dd -(0x1BADB002 + 0x00000003)

section .text
global _start
extern kernel_main

_start:
    ; GRUB already set up protected mode, paging off, interrupts off
    ; EAX contains magic value 0x2BADB002
    ; EBX contains address of multiboot info structure

    ; Set up stack
    mov esp, stack_top

    ; Call kernel main
    call kernel_main

    ; Hang if kernel returns
.hang:
    cli
    hlt
    jmp .hang

section .bss
align 16
stack_bottom:
    resb 16384  ; 16 KB stack
stack_top:
