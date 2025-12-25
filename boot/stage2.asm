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

    ; Load kernel from disk in two parts (some BIOSes limit sectors per read)
    ; Part 1: Load first 64KB (128 sectors) to 0x10000
    mov ah, 0x42            ; Extended read
    mov dl, [boot_drive]
    mov si, dap1            ; Disk Address Packet 1
    int 0x13
    jc disk_error

    ; Part 2: Load next 16KB (32 sectors) to 0x20000
    mov ah, 0x42            ; Extended read
    mov dl, [boot_drive]
    mov si, dap2            ; Disk Address Packet 2
    int 0x13
    jc disk_error

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

; Disk Address Packets for LBA read (split into two reads)
align 4
dap1:
    db 16           ; Size of DAP (16 bytes)
    db 0            ; Reserved
    dw 127          ; Number of sectors to read (127 * 512 = 64KB - 512)
    dw 0x0000       ; Offset (0)
    dw 0x1000       ; Segment (0x1000 -> address 0x10000)
    dd 18           ; LBA low 32 bits (sector 18)
    dd 0            ; LBA high 32 bits

align 4
dap2:
    db 16           ; Size of DAP (16 bytes)
    db 0            ; Reserved
    dw 120          ; Number of sectors to read (120 * 512 = 60KB for remainder, supports ~124KB kernel)
    dw 0x0000       ; Offset (0)
    dw 0x1FE0       ; Segment (0x1FE0 * 16 = 0x1FE00, right after first 127 sectors)
    dd 145          ; LBA low 32 bits (sector 18 + 127 = 145)
    dd 0            ; LBA high 32 bits
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
