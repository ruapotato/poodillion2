; Simple test kernel in pure assembly
bits 32

section .text
global main

main:
    ; Write "HI" to VGA memory
    mov byte [0xB8000], 'H'
    mov byte [0xB8001], 0x0F
    mov byte [0xB8002], 'I'
    mov byte [0xB8003], 0x0F

    ; Infinite halt loop
.halt:
    hlt
    jmp .halt
