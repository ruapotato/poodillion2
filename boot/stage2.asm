; stage2.asm - PoodillionOS Stage 2 Bootloader
; Loaded by stage 1, switches to protected mode and loads kernel

[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Print stage 2 message
    mov si, msg_stage2
    call print_string

    ; Load kernel from disk (in real mode, before protected mode)
    mov si, msg_loading_kernel
    call print_string
    call load_kernel_real

    ; Enable A20 line (access memory above 1MB)
    call enable_a20

    ; Load GDT
    lgdt [gdt_descriptor]

    ; Switch to protected mode
    mov eax, cr0
    or eax, 1               ; Set PE (Protection Enable) bit
    mov cr0, eax

    ; Far jump to flush pipeline and switch to 32-bit
    jmp 0x08:protected_mode_start

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

; Load kernel from disk (16-bit real mode)
; Loads kernel from sector 18 to 0x10000 (64KB mark)
load_kernel_real:
    push ax
    push bx
    push cx
    push dx

    mov ah, 0x02            ; BIOS read sectors
    mov al, 32              ; Read 32 sectors (16KB - enough for small kernel)
    mov ch, 0               ; Cylinder 0
    mov cl, 18              ; Sector 18 (where kernel starts)
    mov dh, 0               ; Head 0
    mov dl, 0x80            ; First hard drive
    mov bx, 0x1000          ; Segment
    mov es, bx
    xor bx, bx              ; Offset 0 (loads to 0x10000)
    int 0x13                ; BIOS disk interrupt

    jc .error

    mov si, msg_kernel_loaded
    call print_string
    jmp .done

.error:
    mov si, msg_kernel_error
    call print_string
    jmp $                   ; Hang on error

.done:
    pop dx
    pop cx
    pop bx
    pop ax
    ret

; Messages
msg_stage2:         db 'Stage 2 running...', 13, 10, 0
msg_loading_kernel: db 'Loading kernel...', 13, 10, 0
msg_kernel_loaded:  db 'Kernel loaded!', 13, 10, 0
msg_kernel_error:   db 'Kernel load error!', 13, 10, 0
msg_a20:            db 'Enabling A20...', 13, 10, 0
msg_pmode:          db 'Entering protected mode...', 13, 10, 0

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

; Segment selectors (offsets into GDT, not addresses!)
CODE_SEG equ 0x08
DATA_SEG equ 0x10

; ======= 32-bit Protected Mode Code =======
[BITS 32]
protected_mode_start:
    cli                     ; Disable interrupts (no IDT set up yet!)

    ; Set up segments
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000        ; Stack at 640KB

    ; Debug: Write 'P' to top-left of screen immediately
    mov byte [0xB8000], 'P'
    mov byte [0xB8001], 0x0F

    ; Print message to VGA (we're in protected mode now!)
    mov edi, 0xB8000        ; VGA text buffer
    mov esi, msg_32bit
    call print_string_pm

    ; Copy kernel from 0x10000 to 0x100000 (1MB)
    ; This moves it above 1MB for proper execution
    mov esi, 0x10000        ; Source: where we loaded it
    mov edi, 0x100000       ; Destination: 1MB mark
    mov ecx, 8192           ; Copy 32KB (8192 dwords)
    rep movsd               ; Copy!

    ; Jump to kernel entry point (_start is at 0x101000, not 0x100000)
    jmp 0x08:0x101000   ; Kernel entry point

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

msg_32bit: db 'Protected mode OK!', 0

; Pad stage 2 to 8KB
times 8192-($-$$) db 0
