; Brainhair Shell Wrapper for BrainhairOS
; Entry point that calls the Brainhair shell

bits 32

extern brainhair_kernel_main

global kernel_main

section .text

kernel_main:
    ; We're already in protected mode thanks to GRUB
    ; Stack is already set up by GRUB
    ; Just call the Brainhair shell
    call brainhair_kernel_main

    ; Should never return, but if it does, halt
.halt:
    cli
    hlt
    jmp .halt
