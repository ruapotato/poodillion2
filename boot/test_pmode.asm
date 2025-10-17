; Minimal protected mode test
; Just enter pmode and write to VGA

[BITS 16]
[ORG 0x7C00]

start:
    ; Setup
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00

    ; Write marker '1' before pmode transition
    mov ax, 0xB800
    mov es, ax
    mov word [es:0], 0x0E31   ; '1' in yellow

    ; Disable interrupts
    cli

    ; Mask all PIC interrupts
    mov al, 0xFF
    out 0xA1, al
    out 0x21, al

    ; Write marker '2'
    mov word [es:2], 0x0E32   ; '2'

    ; Load GDT
    lgdt [gdt_descriptor]

    ; Write marker '3'
    mov word [es:4], 0x0E33   ; '3'

    ; Enter protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    ; Write marker '4' (still in 16-bit mode)
    mov word [es:6], 0x0E34   ; '4'

    ; Far jump to 32-bit code
    jmp 0x08:pmode32

; GDT
align 8
gdt_start:
    dq 0                        ; Null descriptor
    dw 0xFFFF, 0x0000           ; Code: limit, base low
    db 0x00, 0x9A, 0xCF, 0x00   ; base mid, access, flags, base high
    dw 0xFFFF, 0x0000           ; Data: limit, base low
    db 0x00, 0x92, 0xCF, 0x00   ; base mid, access, flags, base high
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

[BITS 32]
pmode32:
    ; Set up segments
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov esp, 0x9000

    ; Write "OK" to VGA at 0xB8000
    mov dword [0xB8000], 0x0F4B0F4F  ; 'O' 'K' in white

    ; Hang
halt:
    hlt
    jmp halt

; Pad and boot signature
times 510-($-$$) db 0
dw 0xAA55
