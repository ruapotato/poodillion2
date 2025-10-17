; Mini-Nim Shell Wrapper for PoodillionOS
; Entry point that calls the Mini-Nim shell

bits 32

extern mininim_kernel_main

global kernel_main

section .text

kernel_main:
    ; We're already in protected mode thanks to GRUB
    ; Stack is already set up by GRUB
    ; Just call the Mini-Nim shell
    call mininim_kernel_main

    ; Should never return, but if it does, halt
.halt:
    cli
    hlt
    jmp .halt
