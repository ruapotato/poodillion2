; boot64.asm - BrainhairOS 64-bit Kernel Entry Point
; Entry point for the kernel when running in long mode

[BITS 64]

section .text

; Kernel constants
KERNEL_STACK_TOP equ 0x200000   ; 2MB

global _start

; External kernel main (64-bit codegen now ready)
extern brainhair_kernel_main

_start:
    ; We're already in long mode with paging enabled
    ; Set up a clean 64-bit environment

    ; Clear all general-purpose registers
    xor rax, rax
    xor rbx, rbx
    xor rcx, rcx
    xor rdx, rdx
    xor rsi, rsi
    xor rdi, rdi
    xor rbp, rbp
    xor r8, r8
    xor r9, r9
    xor r10, r10
    xor r11, r11
    xor r12, r12
    xor r13, r13
    xor r14, r14
    xor r15, r15

    ; Set up segment registers (already done by bootloader, but be safe)
    mov ax, 0x10            ; Data segment
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Set up stack
    mov rsp, KERNEL_STACK_TOP

    ; Clear direction flag
    cld

    ; Write "KN" to VGA to show kernel is running
    mov dword [0xB8014], 0x0F4E0F4B  ; 'KN' in white

    ; Zero BSS section
    extern __bss_start
    extern __bss_end

    mov rdi, __bss_start
    mov rcx, __bss_end
    sub rcx, rdi
    shr rcx, 3              ; Divide by 8 (qwords)
    xor rax, rax
    rep stosq

    ; Handle any remaining bytes
    mov rdi, __bss_start
    mov rcx, __bss_end
    sub rcx, rdi
    and rcx, 7              ; Remaining bytes
    rep stosb

    ; Initialize IDT before kernel
    extern setup_idt64
    call setup_idt64

    ; Call the kernel main function
    call brainhair_kernel_main

    ; If kernel returns, halt
.halt:
    hlt
    jmp .halt

; Utility functions for kernel

; memset - Set memory to a value
; RDI = destination, RSI = value (byte), RDX = count
global memset
memset:
    push rdi
    mov rax, rsi            ; Value
    mov rcx, rdx            ; Count
    rep stosb
    pop rax                 ; Return original destination
    ret

; memcpy - Copy memory
; RDI = destination, RSI = source, RDX = count
global memcpy
memcpy:
    push rdi
    mov rcx, rdx
    rep movsb
    pop rax                 ; Return original destination
    ret

; net_memset - For compatibility with existing kernel code
global net_memset
net_memset:
    ; RDI = dest, RSI = val, RDX = len
    push rdi
    mov rax, rsi
    mov rcx, rdx
    rep stosb
    pop rax
    ret

section .bss
    resq 1                  ; Reserve space to ensure BSS exists
