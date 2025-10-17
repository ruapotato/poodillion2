; Shell Kernel Wrapper for PoodillionOS
; This is the entry point called by GRUB
; Sets up the stack and calls the shell

bits 32

extern shell_main

global kernel_main

section .text

kernel_main:
    ; We're already in protected mode thanks to GRUB
    ; Stack is already set up by GRUB
    ; Just call the shell
    call shell_main

    ; Should never return, but if it does, halt
.halt:
    cli
    hlt
    jmp .halt
