; devfs.asm - Device filesystem for BrainhairOS
; Implements /dev with character and block device nodes

bits 32

; Device types
DEV_TYPE_CHAR   equ 1       ; Character device
DEV_TYPE_BLOCK  equ 2       ; Block device

; Device major numbers (like Linux)
DEV_MAJOR_MEM   equ 1       ; Memory devices (null, zero, full, random)
DEV_MAJOR_TTY   equ 5       ; TTY devices
DEV_MAJOR_HD    equ 3       ; IDE hard disks
DEV_MAJOR_SD    equ 8       ; SCSI/SATA disks

; Minor numbers for memory devices
DEV_MINOR_NULL  equ 3       ; /dev/null
DEV_MINOR_ZERO  equ 5       ; /dev/zero
DEV_MINOR_FULL  equ 7       ; /dev/full

; Minor numbers for TTY
DEV_MINOR_TTY   equ 0       ; /dev/tty (current tty)
DEV_MINOR_CONSOLE equ 1     ; /dev/console

; Device node entry structure (32 bytes)
; Offset  Size  Field
; 0       4     Name pointer (or 0 if unused)
; 4       1     Type (DEV_TYPE_CHAR or DEV_TYPE_BLOCK)
; 5       1     Major number
; 6       2     Minor number
; 8       4     Read function pointer
; 12      4     Write function pointer
; 16      4     Ioctl function pointer
; 20      4     Private data
; 24      8     Reserved

DEVNODE_SIZE    equ 32
MAX_DEVICES     equ 32

; External references
extern serial_putchar
extern serial_getchar
extern serial_available
extern ata_read_sectors_pio
extern ata_write_sectors_pio

section .data

; Static device names
dev_null_name:  db "null", 0
dev_zero_name:  db "zero", 0
dev_full_name:  db "full", 0
dev_tty_name:   db "tty", 0
dev_console_name: db "console", 0
dev_random_name: db "random", 0
dev_urandom_name: db "urandom", 0
dev_hda_name:   db "hda", 0
dev_hdb_name:   db "hdb", 0

; Device count
global devfs_device_count
devfs_device_count:
    dd 0

section .bss

; Device node table
align 4
global devfs_devices
devfs_devices:
    resb DEVNODE_SIZE * MAX_DEVICES

section .text

; ============================================================================
; devfs_init - Initialize the device filesystem
; ============================================================================
global devfs_init
devfs_init:
    push eax
    push ecx
    push edi

    ; Clear device table
    mov edi, devfs_devices
    mov ecx, DEVNODE_SIZE * MAX_DEVICES / 4
    xor eax, eax
    rep stosd

    mov dword [devfs_device_count], 0

    ; Register built-in devices

    ; /dev/null
    push dev_null_write           ; write handler
    push dev_null_read            ; read handler
    push (DEV_MINOR_NULL << 8) | DEV_MAJOR_MEM  ; minor << 8 | major
    push DEV_TYPE_CHAR            ; type
    push dev_null_name            ; name
    call devfs_register
    add esp, 20

    ; /dev/zero
    push dev_zero_write           ; write handler
    push dev_zero_read            ; read handler
    push (DEV_MINOR_ZERO << 8) | DEV_MAJOR_MEM
    push DEV_TYPE_CHAR
    push dev_zero_name
    call devfs_register
    add esp, 20

    ; /dev/full
    push dev_full_write           ; write handler
    push dev_full_read            ; read handler
    push (DEV_MINOR_FULL << 8) | DEV_MAJOR_MEM
    push DEV_TYPE_CHAR
    push dev_full_name
    call devfs_register
    add esp, 20

    ; /dev/tty (serial console for now)
    push dev_tty_write
    push dev_tty_read
    push (DEV_MINOR_TTY << 8) | DEV_MAJOR_TTY
    push DEV_TYPE_CHAR
    push dev_tty_name
    call devfs_register
    add esp, 20

    ; /dev/console
    push dev_tty_write            ; Same as tty for now
    push dev_tty_read
    push (DEV_MINOR_CONSOLE << 8) | DEV_MAJOR_TTY
    push DEV_TYPE_CHAR
    push dev_console_name
    call devfs_register
    add esp, 20

    ; /dev/random (pseudo-random, just uses counter for now)
    push dev_zero_write           ; Write discards
    push dev_random_read          ; Random read
    push (8 << 8) | DEV_MAJOR_MEM ; minor 8 = random
    push DEV_TYPE_CHAR
    push dev_random_name
    call devfs_register
    add esp, 20

    ; /dev/urandom (same as random for now)
    push dev_zero_write
    push dev_random_read
    push (9 << 8) | DEV_MAJOR_MEM ; minor 9 = urandom
    push DEV_TYPE_CHAR
    push dev_urandom_name
    call devfs_register
    add esp, 20

    ; Block devices (hda, hdb) registered elsewhere by ATA driver

    pop edi
    pop ecx
    pop eax
    ret

; ============================================================================
; devfs_register - Register a device node
; Input:
;   [esp+4]  = name pointer
;   [esp+8]  = type (DEV_TYPE_CHAR or DEV_TYPE_BLOCK)
;   [esp+12] = (minor << 8) | major
;   [esp+16] = read handler
;   [esp+20] = write handler
; Returns: EAX = device index, or -1 on error
; ============================================================================
global devfs_register
devfs_register:
    push ebx
    push ecx
    push edi

    ; Find free slot
    mov ecx, [devfs_device_count]
    cmp ecx, MAX_DEVICES
    jge .no_slot

    ; Calculate offset
    mov eax, ecx
    imul eax, DEVNODE_SIZE
    add eax, devfs_devices
    mov edi, eax

    ; Fill in device node
    mov eax, [esp + 16]         ; name
    mov [edi + 0], eax

    mov eax, [esp + 20]         ; type
    mov [edi + 4], al

    mov eax, [esp + 24]         ; major/minor
    mov [edi + 5], al           ; major
    shr eax, 8
    mov [edi + 6], ax           ; minor (16-bit)

    mov eax, [esp + 28]         ; read handler
    mov [edi + 8], eax

    mov eax, [esp + 32]         ; write handler
    mov [edi + 12], eax

    mov dword [edi + 16], 0     ; ioctl (NULL)
    mov dword [edi + 20], 0     ; private data

    ; Increment count and return index
    mov eax, ecx
    inc dword [devfs_device_count]

    pop edi
    pop ecx
    pop ebx
    ret

.no_slot:
    mov eax, -1
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; devfs_lookup - Find a device by name
; Input: [esp+4] = name pointer
; Returns: EAX = device index, or -1 if not found
; ============================================================================
global devfs_lookup
devfs_lookup:
    push ebx
    push ecx
    push esi
    push edi

    mov esi, [esp + 20]         ; name to find
    mov ecx, 0
    mov edi, devfs_devices

.lookup_loop:
    cmp ecx, [devfs_device_count]
    jge .not_found

    ; Get device name pointer
    mov eax, [edi]
    test eax, eax
    jz .lookup_next

    ; Compare names
    push ecx
    push edi
    push esi
    push eax
    call devfs_strcmp
    add esp, 8
    pop edi
    pop ecx

    test eax, eax
    jz .found

.lookup_next:
    add edi, DEVNODE_SIZE
    inc ecx
    jmp .lookup_loop

.found:
    mov eax, ecx
    pop edi
    pop esi
    pop ecx
    pop ebx
    ret

.not_found:
    mov eax, -1
    pop edi
    pop esi
    pop ecx
    pop ebx
    ret

; ============================================================================
; devfs_strcmp - Compare two strings
; Input: [esp+4] = s1, [esp+8] = s2
; Returns: EAX = 0 if equal, non-zero otherwise
; ============================================================================
devfs_strcmp:
    push esi
    push edi

    mov esi, [esp + 12]         ; s1
    mov edi, [esp + 16]         ; s2

.cmp_loop:
    mov al, [esi]
    mov ah, [edi]
    cmp al, ah
    jne .not_equal

    test al, al
    jz .equal

    inc esi
    inc edi
    jmp .cmp_loop

.equal:
    xor eax, eax
    pop edi
    pop esi
    ret

.not_equal:
    mov eax, 1
    pop edi
    pop esi
    ret

; ============================================================================
; devfs_read - Read from a device
; Input:
;   [esp+4]  = device index
;   [esp+8]  = buffer pointer
;   [esp+12] = count
; Returns: EAX = bytes read, or -1 on error
; ============================================================================
global devfs_read
devfs_read:
    push ebx
    push edi

    mov eax, [esp + 12]         ; device index
    cmp eax, [devfs_device_count]
    jge .read_error

    ; Calculate device node offset
    imul eax, DEVNODE_SIZE
    add eax, devfs_devices
    mov edi, eax

    ; Check if device exists
    mov eax, [edi]
    test eax, eax
    jz .read_error

    ; Get read handler
    mov eax, [edi + 8]
    test eax, eax
    jz .read_error

    ; Call read handler(buf, count, private_data)
    push dword [edi + 20]       ; private data
    push dword [esp + 24]       ; count
    push dword [esp + 24]       ; buf
    call eax
    add esp, 12

    pop edi
    pop ebx
    ret

.read_error:
    mov eax, -1
    pop edi
    pop ebx
    ret

; ============================================================================
; devfs_write - Write to a device
; Input:
;   [esp+4]  = device index
;   [esp+8]  = buffer pointer
;   [esp+12] = count
; Returns: EAX = bytes written, or -1 on error
; ============================================================================
global devfs_write
devfs_write:
    push ebx
    push edi

    mov eax, [esp + 12]         ; device index
    cmp eax, [devfs_device_count]
    jge .write_error

    ; Calculate device node offset
    imul eax, DEVNODE_SIZE
    add eax, devfs_devices
    mov edi, eax

    ; Check if device exists
    mov eax, [edi]
    test eax, eax
    jz .write_error

    ; Get write handler
    mov eax, [edi + 12]
    test eax, eax
    jz .write_error

    ; Call write handler(buf, count, private_data)
    push dword [edi + 20]       ; private data
    push dword [esp + 24]       ; count
    push dword [esp + 24]       ; buf
    call eax
    add esp, 12

    pop edi
    pop ebx
    ret

.write_error:
    mov eax, -1
    pop edi
    pop ebx
    ret

; ============================================================================
; devfs_get_name - Get device name
; Input: [esp+4] = device index
; Returns: EAX = name pointer, or 0 if invalid
; ============================================================================
global devfs_get_name
devfs_get_name:
    mov eax, [esp + 4]
    cmp eax, [devfs_device_count]
    jge .invalid

    imul eax, DEVNODE_SIZE
    add eax, devfs_devices
    mov eax, [eax]              ; Get name pointer
    ret

.invalid:
    xor eax, eax
    ret

; ============================================================================
; devfs_get_type - Get device type
; Input: [esp+4] = device index
; Returns: EAX = type (1=char, 2=block), or 0 if invalid
; ============================================================================
global devfs_get_type
devfs_get_type:
    mov eax, [esp + 4]
    cmp eax, [devfs_device_count]
    jge .invalid_type

    imul eax, DEVNODE_SIZE
    add eax, devfs_devices
    movzx eax, byte [eax + 4]   ; Get type
    ret

.invalid_type:
    xor eax, eax
    ret

; ============================================================================
; devfs_get_device_count - Get number of registered devices
; Returns: EAX = device count
; ============================================================================
global devfs_get_device_count
devfs_get_device_count:
    mov eax, [devfs_device_count]
    ret

; ============================================================================
; Device handler implementations
; ============================================================================

; /dev/null read - always returns 0 (EOF)
dev_null_read:
    xor eax, eax
    ret

; /dev/null write - discards data, returns count
dev_null_write:
    mov eax, [esp + 8]          ; count
    ret

; /dev/zero read - fills buffer with zeros
dev_zero_read:
    push ecx
    push edi

    mov edi, [esp + 12]         ; buf
    mov ecx, [esp + 16]         ; count
    xor eax, eax

    test ecx, ecx
    jz .zero_done

    push ecx                    ; Save count for return
    rep stosb
    pop eax                     ; Return count

.zero_done:
    pop edi
    pop ecx
    ret

; /dev/zero write - discards data, returns count
dev_zero_write:
    mov eax, [esp + 8]          ; count
    ret

; /dev/full read - same as zero
dev_full_read:
    jmp dev_zero_read

; /dev/full write - always returns ENOSPC (-28)
dev_full_write:
    mov eax, -28                ; ENOSPC
    ret

; /dev/tty read - read from serial console
dev_tty_read:
    push ebx
    push ecx
    push edi

    mov edi, [esp + 16]         ; buf
    mov ecx, [esp + 20]         ; count
    xor ebx, ebx                ; bytes read

    test ecx, ecx
    jz .tty_read_done

.tty_read_loop:
    ; Check if data available
    call serial_available
    test eax, eax
    jz .tty_read_done           ; No data, return what we have

    ; Read a character
    call serial_getchar
    mov [edi + ebx], al
    inc ebx

    cmp ebx, ecx
    jl .tty_read_loop

.tty_read_done:
    mov eax, ebx
    pop edi
    pop ecx
    pop ebx
    ret

; /dev/tty write - write to serial console
dev_tty_write:
    push ebx
    push ecx
    push esi

    mov esi, [esp + 16]         ; buf
    mov ecx, [esp + 20]         ; count
    xor ebx, ebx                ; bytes written

    test ecx, ecx
    jz .tty_write_done

.tty_write_loop:
    movzx eax, byte [esi + ebx]
    push eax
    call serial_putchar
    add esp, 4
    inc ebx

    cmp ebx, ecx
    jl .tty_write_loop

.tty_write_done:
    mov eax, ebx
    pop esi
    pop ecx
    pop ebx
    ret

; /dev/random read - pseudo-random bytes (using tick counter)
section .data
random_seed: dd 12345

section .text
dev_random_read:
    push ebx
    push ecx
    push edi

    mov edi, [esp + 16]         ; buf
    mov ecx, [esp + 20]         ; count
    xor ebx, ebx                ; bytes generated

    test ecx, ecx
    jz .random_done

.random_loop:
    ; Simple LCG: seed = (seed * 1103515245 + 12345) & 0x7fffffff
    mov eax, [random_seed]
    imul eax, 1103515245
    add eax, 12345
    and eax, 0x7fffffff
    mov [random_seed], eax

    ; Use high byte as random
    shr eax, 16
    mov [edi + ebx], al
    inc ebx

    cmp ebx, ecx
    jl .random_loop

.random_done:
    mov eax, ebx
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; devfs_register_block - Register a block device (for ATA driver to call)
; Input:
;   [esp+4]  = name pointer
;   [esp+8]  = drive number
; Returns: EAX = device index, or -1 on error
; ============================================================================
global devfs_register_block
devfs_register_block:
    push ebx
    push ecx
    push edi

    ; Find free slot
    mov ecx, [devfs_device_count]
    cmp ecx, MAX_DEVICES
    jge .block_no_slot

    ; Calculate offset
    mov eax, ecx
    imul eax, DEVNODE_SIZE
    add eax, devfs_devices
    mov edi, eax

    ; Fill in device node
    mov eax, [esp + 16]         ; name
    mov [edi + 0], eax

    mov byte [edi + 4], DEV_TYPE_BLOCK
    mov byte [edi + 5], DEV_MAJOR_HD    ; major

    mov eax, [esp + 20]         ; drive number = minor
    mov [edi + 6], ax

    mov dword [edi + 8], dev_block_read
    mov dword [edi + 12], dev_block_write
    mov dword [edi + 16], 0     ; ioctl
    mov eax, [esp + 20]         ; private data = drive number
    mov [edi + 20], eax

    ; Increment count and return index
    mov eax, ecx
    inc dword [devfs_device_count]

    pop edi
    pop ecx
    pop ebx
    ret

.block_no_slot:
    mov eax, -1
    pop edi
    pop ecx
    pop ebx
    ret

; Block device read - uses ATA driver
dev_block_read:
    ; Args: buf, count, drive_number
    ; For now, just return 0 - full block device access needs more infrastructure
    xor eax, eax
    ret

; Block device write - uses ATA driver
dev_block_write:
    ; Args: buf, count, drive_number
    xor eax, eax
    ret
