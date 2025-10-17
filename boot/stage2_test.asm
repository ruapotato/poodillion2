; stage2_test.asm - Simple protected mode test
; Just enter protected mode and write to VGA, no kernel loading

[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Print message
    mov si, msg_test
    call print_string

    ; Disable interrupts
    cli

    ; Load GDT
    lgdt [gdt_descriptor]

    ; Enter protected mode
    mov eax, cr0
    or al, 1
    mov cr0, eax

    ; Far jump using explicit bytes
    db 0x66  ; operand size override
    db 0xEA  ; far jump opcode
    dd protected_mode_start  ; offset
    dw 0x08  ; segment

; Print null-terminated string (16-bit real mode)
print_string:
    pusha
.loop:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0E
    mov bh, 0
    int 0x10
    jmp .loop
.done:
    popa
    ret

; Messages
msg_test: db 'Testing protected mode...', 13, 10, 0

; GDT (Global Descriptor Table)
align 8
gdt_start:
    ; Null descriptor
    dq 0

    ; Code segment: base=0, limit=4GB, 32-bit, executable, readable
    dw 0xFFFF       ; Limit 0-15
    dw 0x0000       ; Base 0-15
    db 0x00         ; Base 16-23
    db 0x9A         ; Access: Present, Ring 0, Code, Executable, Readable
    db 0xCF         ; Flags: 4KB granularity, 32-bit, Limit 16-19 = 0xF
    db 0x00         ; Base 24-31

    ; Data segment: base=0, limit=4GB, 32-bit, writable
    dw 0xFFFF       ; Limit 0-15
    dw 0x0000       ; Base 0-15
    db 0x00         ; Base 16-23
    db 0x92         ; Access: Present, Ring 0, Data, Writable
    db 0xCF         ; Flags: 4KB granularity, 32-bit
    db 0x00         ; Base 24-31
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

; ======= 32-bit Protected Mode Code =======
[BITS 32]
protected_mode_start:
    ; Set up segments
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000

    ; Write "PMODE OK" to VGA
    mov edi, 0xB8000
    mov eax, 0x0F500F50  ; 'PP' white on black
    stosd
    mov eax, 0x0F4D0F4D  ; 'MM' white on black
    stosd
    mov eax, 0x0F4F0F4F  ; 'OO' white on black
    stosd
    mov eax, 0x0F440F44  ; 'DD' white on black
    stosd
    mov eax, 0x0F450F45  ; 'EE' white on black
    stosd

    ; Halt
    cli
    hlt
    jmp $

; Pad to 8KB
times 8192-($-$$) db 0
