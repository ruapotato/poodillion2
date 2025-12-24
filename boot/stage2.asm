; stage2.asm - BrainhairOS Stage 2 Bootloader
; Loads kernel from disk and enters protected mode

[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Save boot drive
    mov [boot_drive], dl

    ; Print stage 2 start message
    mov si, msg_stage2
    call print_string

    ; Load kernel from disk (in real mode, using BIOS)
    ; Kernel is at LBA 18 (dd seek=18), but INT 13h uses 1-based sectors
    ; LBA 18 = sector 19 for INT 13h (since sectors are 1-based: LBA = sector - 1)
    mov ah, 0x02            ; BIOS read sectors
    mov al, 64              ; Read 64 sectors (32KB kernel)
    mov ch, 0               ; Cylinder 0
    mov cl, 19              ; Sector 19 (1-based) = LBA 18 (0-based)
    mov dh, 0               ; Head 0
    mov dl, [boot_drive]    ; Drive number
    mov bx, 0x1000          ; Segment
    mov es, bx
    xor bx, bx              ; Offset 0 (load to 0x10000)
    int 0x13                ; BIOS disk read

    jc disk_error           ; Check if read failed

    ; Print kernel loaded message
    mov si, msg_kernel_loaded
    call print_string
    jmp after_disk_load

disk_error:
    mov si, msg_disk_error
    call print_string
    cli
    hlt

after_disk_load:

    ; Print protected mode message NOW, before any hardware changes
    mov si, msg_pmode
    call print_string

    ; Write marker '1' to show we got here
    mov ax, 0xB800
    mov es, ax
    mov word [es:0], 0x0E31   ; '1' in yellow (before A20)

    ; Enable A20 (fast method)
    in al, 0x92
    or al, 2
    out 0x92, al

    ; Write marker '2' to show A20 is done
    mov word [es:2], 0x0E32   ; '2' in yellow (after A20)

    ; Disable interrupts
    cli

    ; Write marker '3' to show interrupts disabled
    mov word [es:4], 0x0E33   ; '3' in yellow (after CLI)

    ; Disable PIC (Programmable Interrupt Controller)
    mov al, 0xFF
    out 0xA1, al        ; Mask all interrupts on slave PIC
    out 0x21, al        ; Mask all interrupts on master PIC

    ; Write marker '4' to show PIC disabled
    mov word [es:6], 0x0E34   ; '4' in yellow (after PIC disable)

    ; Load GDT
    lgdt [gdt_descriptor]

    ; Write marker '5' to show GDT loaded
    mov word [es:8], 0x0E35   ; '5' in yellow (after LGDT)

    ; Enter protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    ; Write marker '6' to show CR0 set (still in real mode addressing)
    mov word [es:10], 0x0E36  ; '6' in yellow (after CR0 set)

    ; Far jump to flush pipeline and enter 32-bit protected mode
    jmp 0x08:protected_mode_start

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
boot_drive: db 0
msg_stage2: db 'Stage 2 running...', 13, 10, 0
msg_kernel_loaded: db 'Kernel loaded from disk', 13, 10, 0
msg_disk_error: db 'DISK READ ERROR!', 13, 10, 0
msg_pmode: db 'Entering protected mode...', 13, 10, 0

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

gdt_descriptor:
    dw gdt_end - gdt_start - 1  ; Size (23 bytes for 3 descriptors)
    dd gdt_start                 ; Offset

; ======= 32-bit Protected Mode Code =======
[BITS 32]
protected_mode_start:
    ; Set up all segment registers
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Set stack (at 640KB, just before VGA memory)
    mov esp, 0x90000

    ; Write "PP" to top-left corner to show we made it to protected mode
    mov dword [0xB8000], 0x0F500F50  ; 'PP' in white on black

    ; Jump to kernel entry point at 0x10000
    jmp 0x08:0x10000

; Pad to 8KB
times 8192-($-$$) db 0
