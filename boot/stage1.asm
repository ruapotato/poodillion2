; stage1.asm - BrainhairOS Stage 1 Bootloader
; This is the first 512 bytes loaded by BIOS
; Loads stage 2 and jumps to it

[BITS 16]
[ORG 0x7C00]

start:
    ; Set up segments
    cli                     ; Disable interrupts
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00          ; Stack grows down from bootloader
    sti                     ; Enable interrupts

    ; Save boot drive (BIOS passes it in DL)
    mov [boot_drive], dl

    ; Print boot message
    mov si, msg_boot
    call print_string

    ; Load stage 2 from disk
    ; Stage 2 is at sector 2 (right after this bootloader)
    mov ah, 0x02            ; BIOS read sectors
    mov al, 16              ; Read 16 sectors (8KB for stage 2)
    mov ch, 0               ; Cylinder 0
    mov cl, 2               ; Sector 2 (sector 1 is this bootloader)
    mov dh, 0               ; Head 0
    mov dl, [boot_drive]    ; Drive number
    mov bx, 0x7E00          ; Load to 0x7E00 (right after bootloader)
    int 0x13                ; BIOS disk interrupt

    jc disk_error           ; Jump if error

    ; Print success message
    mov si, msg_loaded
    call print_string

    ; Jump to stage 2
    jmp 0x0000:0x7E00

disk_error:
    mov si, msg_error
    call print_string
    jmp $                   ; Hang

; Print null-terminated string
; SI = pointer to string
print_string:
    pusha
.loop:
    lodsb                   ; Load byte from SI into AL
    or al, al               ; Check if null
    jz .done
    mov ah, 0x0E            ; BIOS teletype output
    mov bh, 0               ; Page 0
    int 0x10                ; BIOS video interrupt
    jmp .loop
.done:
    popa
    ret

; Data
boot_drive: db 0            ; BIOS passes boot drive in DL
msg_boot:   db 'BrainhairOS Stage 1...', 13, 10, 0
msg_loaded: db 'Stage 2 loaded', 13, 10, 0
msg_error:  db 'Disk read error!', 13, 10, 0

; Pad to 510 bytes and add boot signature
times 510-($-$$) db 0
dw 0xAA55                   ; Boot signature
