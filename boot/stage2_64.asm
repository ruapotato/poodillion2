; stage2_64.asm - BrainhairOS Stage 2 Bootloader (64-bit Long Mode)
; Loads kernel from disk and enters 64-bit long mode

[BITS 16]
[ORG 0x7E00]

stage2_start:
    ; Save boot drive
    mov [boot_drive], dl

    ; Print stage 2 start message
    mov si, msg_stage2
    call print_string

    ; Load kernel from disk in multiple parts (BIOS limits sectors per read)
    ; Part 1: Load first 64KB (127 sectors) to 0x10000
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap1
    int 0x13
    jc disk_error

    ; Part 2: Load next 60KB (120 sectors) to 0x1FE00
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap2
    int 0x13
    jc disk_error

    ; Part 3: Load another 64KB (127 sectors)
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap3
    int 0x13
    jc disk_error

    ; Part 4: Load another 64KB (127 sectors)
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap4
    int 0x13
    jc disk_error

    ; Part 5: Load another 64KB (127 sectors)
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap5
    int 0x13
    jc disk_error

    ; Part 6: Load another 64KB (127 sectors)
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap6
    int 0x13
    jc disk_error

    ; Part 7: Load final 64KB (127 sectors) - total ~444KB capacity
    mov ah, 0x42
    mov dl, [boot_drive]
    mov si, dap7
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
    ; Check for CPUID support
    pushfd
    pop eax
    mov ecx, eax
    xor eax, 0x200000       ; Flip ID bit
    push eax
    popfd
    pushfd
    pop eax
    xor eax, ecx
    jz .no_cpuid

    ; Check for long mode support (CPUID.80000001h:EDX bit 29)
    mov eax, 0x80000000
    cpuid
    cmp eax, 0x80000001
    jb .no_long_mode
    mov eax, 0x80000001
    cpuid
    test edx, 1 << 29       ; LM bit
    jz .no_long_mode
    jmp .has_long_mode

.no_cpuid:
    mov si, msg_no_cpuid
    call print_string
    cli
    hlt

.no_long_mode:
    mov si, msg_no_long_mode
    call print_string
    cli
    hlt

.has_long_mode:
    mov si, msg_long_mode
    call print_string

    ; Enable A20 (fast method)
    in al, 0x92
    or al, 2
    out 0x92, al

    ; Disable interrupts
    cli

    ; Disable PIC
    mov al, 0xFF
    out 0xA1, al
    out 0x21, al

    ; Load 32-bit GDT first (for protected mode transition)
    lgdt [gdt32_descriptor]

    ; Enter protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    ; Far jump to 32-bit protected mode
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

; Data
boot_drive: db 0
msg_stage2: db 'Stage 2 (64-bit) running...', 13, 10, 0
msg_kernel_loaded: db 'Kernel loaded from disk', 13, 10, 0
msg_disk_error: db 'DISK READ ERROR!', 13, 10, 0
msg_no_cpuid: db 'ERROR: CPUID not supported', 13, 10, 0
msg_no_long_mode: db 'ERROR: Long mode not supported', 13, 10, 0
msg_long_mode: db 'Long mode supported, entering...', 13, 10, 0

; Disk Address Packets for LBA read
align 4
dap1:
    db 16, 0
    dw 127
    dw 0x0000
    dw 0x1000
    dd 18
    dd 0

align 4
dap2:
    db 16, 0
    dw 120
    dw 0x0000
    dw 0x1FE0
    dd 145
    dd 0

align 4
dap3:
    db 16, 0
    dw 127
    dw 0x0000
    dw 0x2EE0
    dd 265
    dd 0

align 4
dap4:
    db 16, 0
    dw 127
    dw 0x0000
    dw 0x3EC0
    dd 392
    dd 0

align 4
dap5:
    db 16, 0
    dw 127
    dw 0x0000
    dw 0x4EA0
    dd 519
    dd 0

align 4
dap6:
    db 16, 0
    dw 127
    dw 0x0000
    dw 0x5E80
    dd 646
    dd 0

dap7:
    db 16, 0
    dw 127
    dw 0x0000
    dw 0x6E60
    dd 773
    dd 0

; 32-bit GDT for protected mode transition
align 8
gdt32_start:
    dq 0                    ; Null descriptor

    ; Code segment (selector 0x08)
    dw 0xFFFF               ; Limit 0-15
    dw 0x0000               ; Base 0-15
    db 0x00                 ; Base 16-23
    db 0x9A                 ; Access: Present, Ring 0, Code, Executable, Readable
    db 0xCF                 ; Flags: 4KB granularity, 32-bit
    db 0x00                 ; Base 24-31

    ; Data segment (selector 0x10)
    dw 0xFFFF               ; Limit 0-15
    dw 0x0000               ; Base 0-15
    db 0x00                 ; Base 16-23
    db 0x92                 ; Access: Present, Ring 0, Data, Writable
    db 0xCF                 ; Flags: 4KB granularity, 32-bit
    db 0x00                 ; Base 24-31
gdt32_end:

gdt32_descriptor:
    dw gdt32_end - gdt32_start - 1
    dd gdt32_start

; ======= 32-bit Protected Mode Code =======
[BITS 32]

protected_mode_start:
    ; Set up segment registers
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x9F000

    ; Write "32" to VGA to show we're in protected mode
    mov dword [0xB8000], 0x0F320F33  ; '32' in white

    ; Copy kernel from 0x10000 to 0x100000 (1MB)
    mov esi, 0x10000
    mov edi, 0x100000
    mov ecx, 131072         ; 512KB / 4 = 131072 dwords
    cld
    rep movsd

    ; Write "CP" to show copy complete
    mov dword [0xB8004], 0x0F500F43  ; 'CP' in white

    ; Set up 4-level page tables for identity mapping
    ; Page tables at 0x1000 (PML4), 0x2000 (PDPT), 0x3000 (PD), 0x4000+ (PTs)

    ; Clear page table area (16KB = 4 tables)
    mov edi, 0x1000
    xor eax, eax
    mov ecx, 4096           ; 16KB / 4 = 4096 dwords
    rep stosd

    ; PML4[0] -> PDPT at 0x2000
    mov dword [0x1000], 0x2003      ; Present + Writable
    mov dword [0x1004], 0

    ; PDPT[0] -> PD at 0x3000
    mov dword [0x2000], 0x3003      ; Present + Writable
    mov dword [0x2004], 0

    ; PD[0] -> PT at 0x4000 (for first 2MB)
    mov dword [0x3000], 0x4003      ; Present + Writable
    mov dword [0x3004], 0

    ; PD[1] -> PT at 0x5000 (for second 2MB, covers kernel at 1MB)
    mov dword [0x3008], 0x5003      ; Present + Writable
    mov dword [0x300C], 0

    ; Fill PT at 0x4000 for first 2MB (identity map 0-2MB)
    mov edi, 0x4000
    mov eax, 0x0003         ; Present + Writable + Physical address 0
    mov ecx, 512
.fill_pt1:
    mov [edi], eax
    mov dword [edi+4], 0
    add eax, 0x1000         ; Next 4KB page
    add edi, 8
    loop .fill_pt1

    ; Fill PT at 0x5000 for second 2MB (identity map 2-4MB)
    mov edi, 0x5000
    mov eax, 0x200003       ; Present + Writable + Physical address 2MB
    mov ecx, 512
.fill_pt2:
    mov [edi], eax
    mov dword [edi+4], 0
    add eax, 0x1000         ; Next 4KB page
    add edi, 8
    loop .fill_pt2

    ; Write "PT" to show page tables set up
    mov dword [0xB8008], 0x0F540F50  ; 'PT' in white

    ; Enable PAE (Physical Address Extension)
    mov eax, cr4
    or eax, 1 << 5          ; PAE bit
    mov cr4, eax

    ; Load CR3 with PML4 address
    mov eax, 0x1000
    mov cr3, eax

    ; Enable long mode in EFER MSR
    mov ecx, 0xC0000080     ; IA32_EFER MSR
    rdmsr
    or eax, 1 << 8          ; LME (Long Mode Enable)
    wrmsr

    ; Enable paging and protection
    mov eax, cr0
    or eax, (1 << 31) | 1   ; PG + PE
    mov cr0, eax

    ; Write "LM" to show long mode enabled
    mov dword [0xB800C], 0x0F4D0F4C  ; 'LM' in white

    ; Load 64-bit GDT
    lgdt [gdt64_descriptor]

    ; Far jump to 64-bit code
    jmp 0x08:long_mode_start

; 64-bit GDT
align 8
gdt64_start:
    dq 0                    ; Null descriptor

    ; 64-bit Code segment (selector 0x08)
    dw 0                    ; Limit (ignored in 64-bit)
    dw 0                    ; Base (ignored)
    db 0                    ; Base (ignored)
    db 0x9A                 ; Access: Present, Ring 0, Code, Executable, Readable
    db 0x20                 ; Flags: Long mode (L bit set)
    db 0                    ; Base (ignored)

    ; 64-bit Data segment (selector 0x10)
    dw 0                    ; Limit (ignored)
    dw 0                    ; Base (ignored)
    db 0                    ; Base (ignored)
    db 0x92                 ; Access: Present, Ring 0, Data, Writable
    db 0                    ; Flags
    db 0                    ; Base (ignored)
gdt64_end:

gdt64_descriptor:
    dw gdt64_end - gdt64_start - 1
    dq gdt64_start

; ======= 64-bit Long Mode Code =======
[BITS 64]

long_mode_start:
    ; Set up 64-bit segment registers
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Set up stack
    mov rsp, 0x200000       ; 2MB

    ; Write "64" to VGA to show we're in long mode
    mov dword [0xB8010], 0x0F340F36  ; '64' in white

    ; Jump to kernel at 1MB
    mov rax, 0x100000
    jmp rax

; Pad to 8KB
times 8192-($-$$) db 0
