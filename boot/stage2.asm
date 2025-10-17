; stage2.asm - PoodillionOS Stage 2 Bootloader
; Loaded by stage 1, switches to protected mode and loads kernel

[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Print stage 2 message
    mov si, msg_stage2
    call print_string

    ; Enable A20 line (access memory above 1MB)
    call enable_a20

    ; Load GDT
    lgdt [gdt_descriptor]

    ; Switch to protected mode
    mov eax, cr0
    or eax, 1               ; Set PE (Protection Enable) bit
    mov cr0, eax

    ; Far jump to flush pipeline and switch to 32-bit
    jmp CODE_SEG:protected_mode_start

; Enable A20 line using keyboard controller
enable_a20:
    push ax
    mov si, msg_a20
    call print_string

    ; Method 1: Fast A20 gate
    in al, 0x92
    or al, 2
    out 0x92, al

    pop ax
    ret

; Print string (16-bit real mode)
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
msg_stage2: db 'Stage 2 running...', 13, 10, 0
msg_a20:    db 'Enabling A20...', 13, 10, 0
msg_pmode:  db 'Entering protected mode...', 13, 10, 0

; GDT (Global Descriptor Table)
gdt_start:
    ; Null descriptor
    dq 0x0000000000000000

    ; Code segment descriptor
    dw 0xFFFF           ; Limit (bits 0-15)
    dw 0x0000           ; Base (bits 0-15)
    db 0x00             ; Base (bits 16-23)
    db 10011010b        ; Access byte: present, ring 0, code, executable, readable
    db 11001111b        ; Flags + Limit (bits 16-19): 4KB granularity, 32-bit
    db 0x00             ; Base (bits 24-31)

    ; Data segment descriptor
    dw 0xFFFF           ; Limit (bits 0-15)
    dw 0x0000           ; Base (bits 0-15)
    db 0x00             ; Base (bits 16-23)
    db 10010010b        ; Access byte: present, ring 0, data, writable
    db 11001111b        ; Flags + Limit (bits 16-19)
    db 0x00             ; Base (bits 24-31)
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1  ; Size
    dd gdt_start                 ; Address

; Segment selectors
CODE_SEG equ gdt_start + 0x08
DATA_SEG equ gdt_start + 0x10

; ======= 32-bit Protected Mode Code =======
[BITS 32]
protected_mode_start:
    ; Set up segments
    mov ax, DATA_SEG
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000        ; Stack at 640KB

    ; Print message to VGA (we're in protected mode now!)
    mov edi, 0xB8000        ; VGA text buffer
    mov esi, msg_32bit
    call print_string_pm

    ; Load kernel from disk
    ; Kernel starts at sector 18 (1 boot + 16 stage2 + 1 padding)
    call load_kernel

    ; Jump to kernel entry point
    jmp CODE_SEG:0x100000   ; Kernel loaded at 1MB

; Print string in 32-bit protected mode
; ESI = pointer to string
; EDI = VGA buffer
print_string_pm:
    pusha
    mov ah, 0x0F            ; White on black
.loop:
    lodsb
    or al, al
    jz .done
    stosw                   ; Write char + attribute
    jmp .loop
.done:
    popa
    ret

; Load kernel from disk (protected mode)
load_kernel:
    ; For now, we'll use a simple method
    ; In real implementation, we'd read from disk using ATA PIO
    ; or parse the filesystem

    ; Kernel is at sector 18, load to 0x100000 (1MB)
    ; This is a placeholder - actual disk I/O would go here

    ret

msg_32bit: db 'Protected mode OK', 0

; Pad stage 2 to 8KB
times 8192-($-$$) db 0
