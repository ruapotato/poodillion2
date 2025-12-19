; Wrapper for Brainhair kernel that adds serial output
bits 32

extern brainhair_kernel_main
extern serial_init
extern serial_print

section .data
msg_banner:     db 10, 10, "========================================", 10
                db "  Brainhair Kernel Booted!", 10
                db "========================================", 10, 10
                db "Compiled from Brainhair source!", 10
                db "Compiler: Brainhair -> x86 assembly", 10
                db "Bootloader: GRUB multiboot", 10, 10
                db "Calling Brainhair kernel_main()...", 10, 0

msg_done:       db 10, "Brainhair kernel_main() returned!", 10
                db "Kernel halted.", 10, 0

section .text
global kernel_main
kernel_main:
    ; Initialize serial port
    call serial_init

    ; Print banner
    mov eax, msg_banner
    call serial_print

    ; Call the actual Brainhair kernel
    call brainhair_kernel_main

    ; Print done message
    mov eax, msg_done
    call serial_print

    ; Halt
.halt:
    hlt
    jmp .halt
