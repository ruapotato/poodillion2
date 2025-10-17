; Ultra-simple stage2 with EXPLICIT GDT
[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Print message
    mov si, msg_s2
    call print_string

    ; Enable A20
    in al, 0x92
    or al, 2
    out 0x92, al

    mov si, msg_a20
    call print_string

    ; Disable interrupts
    cli

    ; Load GDT
    lgdt [gdt_desc]

    ; Enter protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    ; Far jump to flush pipeline - EXPLICIT CODE SEGMENT
    jmp 0x0008:pm_start

print_string:
    pusha
.loop:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0E
    int 0x10
    jmp .loop
.done:
    popa
    ret

msg_s2: db 'S2 ', 0
msg_a20: db 'A20 ', 0

; GDT - EXPLICIT FULL FORMAT
align 16
gdt_start:
    ; Null descriptor (8 bytes)
    dd 0x00000000
    dd 0x00000000

    ; Code segment descriptor (8 bytes) - selector 0x08
    dw 0xFFFF       ; Limit 0-15
    dw 0x0000       ; Base 0-15
    db 0x00         ; Base 16-23
    db 0x9A         ; Access: present, ring 0, code, executable, readable
    db 0xCF         ; Flags: 4KB granularity, 32-bit, limit 16-19
    db 0x00         ; Base 24-31

    ; Data segment descriptor (8 bytes) - selector 0x10
    dw 0xFFFF       ; Limit 0-15
    dw 0x0000       ; Base 0-15
    db 0x00         ; Base 16-23
    db 0x92         ; Access: present, ring 0, data, writable
    db 0xCF         ; Flags: 4KB granularity, 32-bit, limit 16-19
    db 0x00         ; Base 24-31
gdt_end:

gdt_desc:
    dw gdt_end - gdt_start - 1      ; Size
    dd gdt_start                     ; Offset

[BITS 32]
pm_start:
    ; Set up data segments - 0x10 is data segment
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000

    ; Write SUCCESS to VGA
    mov dword [0xB8000], 0x0F570F4F    ; 'O' and 'W'
    mov dword [0xB8004], 0x0F4B0F52    ; 'R' and 'K'

    ; Infinite halt
.halt:
    hlt
    jmp .halt

; Pad to 8KB
times 8192-($-$$) db 0
