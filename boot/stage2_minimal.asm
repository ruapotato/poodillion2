; stage2_minimal.asm - Absolutely minimal protected mode test
; NO BIOS calls, just straight to protected mode
[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Enable A20 (fast method, no BIOS)
    in al, 0x92
    or al, 2
    out 0x92, al

    ; Disable interrupts
    cli

    ; Load GDT
    lgdt [gdt_desc]

    ; Enter protected mode
    mov eax, cr0
    or al, 1
    mov cr0, eax

    ; Far jump to 32-bit code (MUST flush pipeline)
    jmp 0x08:protected_mode

[BITS 32]
protected_mode:
    ; Set up all segment registers
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Set stack
    mov esp, 0x90000

    ; Write directly to VGA memory - "OK!"
    ; VGA text mode at 0xB8000, white on black (0x0F)
    mov byte [0xB8000], 'O'
    mov byte [0xB8001], 0x0F
    mov byte [0xB8002], 'K'
    mov byte [0xB8003], 0x0F
    mov byte [0xB8004], '!'
    mov byte [0xB8005], 0x0F

    ; Halt
.halt:
    hlt
    jmp .halt

; GDT (Global Descriptor Table)
align 8
gdt_start:
    ; Null descriptor (required)
    dq 0

    ; Code segment descriptor (selector 0x08)
    dw 0xFFFF       ; Limit 0-15
    dw 0x0000       ; Base 0-15
    db 0x00         ; Base 16-23
    db 0x9A         ; Access: Present, Ring 0, Code, Executable, Readable
    db 0xCF         ; Flags: 4KB granularity, 32-bit, Limit 16-19 = 0xF
    db 0x00         ; Base 24-31

    ; Data segment descriptor (selector 0x10)
    dw 0xFFFF       ; Limit 0-15
    dw 0x0000       ; Base 0-15
    db 0x00         ; Base 16-23
    db 0x92         ; Access: Present, Ring 0, Data, Writable
    db 0xCF         ; Flags: 4KB granularity, 32-bit, Limit 16-19 = 0xF
    db 0x00         ; Base 24-31
gdt_end:

gdt_desc:
    dw gdt_end - gdt_start - 1  ; Size (23 bytes for 3 descriptors)
    dd gdt_start                 ; Offset

; Pad to 8KB
times 8192-($-$$) db 0
