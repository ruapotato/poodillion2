; stage2_fixed.asm - CORRECT minimal bootloader
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

    ; Print A20 done
    mov si, msg_a20
    call print_string

    ; Load GDT
    lgdt [gdt_desc]

    ; Enter protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    ; Jump to 32-bit code
    jmp 0x08:pm_start

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

msg_s2: db 'S2OK ', 0
msg_a20: db 'A20+ ', 0

; GDT - CORRECT format
align 8
gdt_start:
    dq 0                    ; Null descriptor
    ; Code segment: base=0, limit=0xFFFFF, 32-bit, executable
    dw 0xFFFF, 0, 0x9A00, 0x00CF
    ; Data segment: base=0, limit=0xFFFFF, 32-bit, writable
    dw 0xFFFF, 0, 0x9200, 0x00CF
gdt_end:

gdt_desc:
    dw gdt_end - gdt_start - 1
    dd gdt_start

[BITS 32]
pm_start:
    ; Set up segments - use CORRECT values (NOT gdt_start+offset!)
    mov ax, 0x10            ; Data segment selector
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov esp, 0x90000

    ; Write to VGA to prove we're here
    mov byte [0xB8000], 'W'
    mov byte [0xB8001], 0x0F
    mov byte [0xB8002], 'I'
    mov byte [0xB8003], 0x0F
    mov byte [0xB8004], 'N'
    mov byte [0xB8005], 0x0F

    ; Halt
.halt:
    hlt
    jmp .halt

times 8192-($-$$) db 0
