; ata.asm - ATA/IDE Disk Driver for BrainhairOS
; Supports PIO mode for reading/writing sectors
;
; ATA Ports (Primary Controller):
;   0x1F0 - Data register (16-bit)
;   0x1F1 - Error register (read) / Features (write)
;   0x1F2 - Sector count
;   0x1F3 - LBA low (bits 0-7)
;   0x1F4 - LBA mid (bits 8-15)
;   0x1F5 - LBA high (bits 16-23)
;   0x1F6 - Drive/Head select + LBA bits 24-27
;   0x1F7 - Status (read) / Command (write)
;   0x3F6 - Alternate status / Device control
;
; ATA Ports (Secondary Controller):
;   0x170-0x177, 0x376

[BITS 32]

; External serial functions for debug
extern serial_putchar

section .data

; ATA command codes
ATA_CMD_READ_SECTORS    equ 0x20    ; Read sectors (PIO)
ATA_CMD_WRITE_SECTORS   equ 0x30    ; Write sectors (PIO)
ATA_CMD_IDENTIFY        equ 0xEC    ; Identify drive
ATA_CMD_FLUSH_CACHE     equ 0xE7    ; Flush write cache

; Status register bits
ATA_SR_BSY      equ 0x80    ; Busy
ATA_SR_DRDY     equ 0x40    ; Drive ready
ATA_SR_DF       equ 0x20    ; Drive fault
ATA_SR_DSC      equ 0x10    ; Drive seek complete
ATA_SR_DRQ      equ 0x08    ; Data request ready
ATA_SR_CORR     equ 0x04    ; Corrected data
ATA_SR_IDX      equ 0x02    ; Index
ATA_SR_ERR      equ 0x01    ; Error

; Primary ATA ports
ATA_PRIMARY_DATA        equ 0x1F0
ATA_PRIMARY_ERROR       equ 0x1F1
ATA_PRIMARY_SECCOUNT    equ 0x1F2
ATA_PRIMARY_LBA_LO      equ 0x1F3
ATA_PRIMARY_LBA_MID     equ 0x1F4
ATA_PRIMARY_LBA_HI      equ 0x1F5
ATA_PRIMARY_DRIVE_HEAD  equ 0x1F6
ATA_PRIMARY_STATUS      equ 0x1F7
ATA_PRIMARY_COMMAND     equ 0x1F7
ATA_PRIMARY_ALT_STATUS  equ 0x3F6
ATA_PRIMARY_CONTROL     equ 0x3F6

; Secondary ATA ports
ATA_SECONDARY_DATA      equ 0x170
ATA_SECONDARY_ERROR     equ 0x171
ATA_SECONDARY_SECCOUNT  equ 0x172
ATA_SECONDARY_LBA_LO    equ 0x173
ATA_SECONDARY_LBA_MID   equ 0x174
ATA_SECONDARY_LBA_HI    equ 0x175
ATA_SECONDARY_DRIVE_HEAD equ 0x176
ATA_SECONDARY_STATUS    equ 0x177
ATA_SECONDARY_COMMAND   equ 0x177
ATA_SECONDARY_ALT_STATUS equ 0x376
ATA_SECONDARY_CONTROL   equ 0x376

section .bss

; IRQ flags set by interrupt handlers
global ata_primary_irq_fired
global ata_secondary_irq_fired
ata_primary_irq_fired:      resd 1
ata_secondary_irq_fired:    resd 1

; 512-byte sector buffer for identify command
global ata_identify_buffer
ata_identify_buffer:        resb 512

section .text

; ============================================================================
; dbg_char - Output a debug character to serial
; Input: al = character to output
; ============================================================================
dbg_char:
    push eax
    push ecx
    push edx
    movzx eax, al
    push eax
    call serial_putchar
    add esp, 4
    pop edx
    pop ecx
    pop eax
    ret

; ============================================================================
; dbg_hex - Output a hex byte to serial
; Input: al = byte to output
; ============================================================================
dbg_hex:
    push eax
    push ebx
    push ecx

    mov bl, al          ; Save original byte

    ; High nibble
    mov al, bl
    shr al, 4
    and al, 0x0F
    cmp al, 10
    jl .high_digit
    add al, 'A' - 10
    jmp .print_high
.high_digit:
    add al, '0'
.print_high:
    call dbg_char

    ; Low nibble
    mov al, bl
    and al, 0x0F
    cmp al, 10
    jl .low_digit
    add al, 'A' - 10
    jmp .print_low
.low_digit:
    add al, '0'
.print_low:
    call dbg_char

    pop ecx
    pop ebx
    pop eax
    ret

; ============================================================================
; ata_delay - Short delay for ATA timing (400ns minimum)
; Reads alternate status 4 times (takes ~400ns each)
; Input: dx = base port (0x1F0 or 0x170)
; ============================================================================
global ata_delay
ata_delay:
    push eax
    push edx

    ; Read alternate status register 4 times
    ; For primary: 0x1F0 + 0x206 = 0x3F6
    ; For secondary: 0x170 + 0x206 = 0x376
    add dx, 0x206

    in al, dx
    in al, dx
    in al, dx
    in al, dx

    pop edx
    pop eax
    ret

; ============================================================================
; ata_wait_bsy - Wait for BSY flag to clear
; Input: dx = status port (0x1F7 or 0x177)
; Returns: EAX = 0 on success, -1 on timeout
; ============================================================================
global ata_wait_bsy
ata_wait_bsy:
    push ecx
    mov ecx, 100000         ; Timeout counter

.loop:
    in al, dx
    test al, ATA_SR_BSY
    jz .done

    dec ecx
    jnz .loop

    ; Timeout
    mov eax, -1
    pop ecx
    ret

.done:
    xor eax, eax
    pop ecx
    ret

; ============================================================================
; ata_wait_drq - Wait for DRQ flag to set (data ready)
; Input: dx = status port (0x1F7 or 0x177)
; Returns: EAX = 0 on success, -1 on timeout/error
; ============================================================================
global ata_wait_drq
ata_wait_drq:
    push ecx
    mov ecx, 100000         ; Timeout counter

.loop:
    in al, dx

    ; Check for error
    test al, ATA_SR_ERR
    jnz .error
    test al, ATA_SR_DF
    jnz .error

    ; Check if data ready
    test al, ATA_SR_DRQ
    jnz .done

    ; Check if still busy
    test al, ATA_SR_BSY
    jnz .loop

    dec ecx
    jnz .loop

    ; Timeout
.error:
    mov eax, -1
    pop ecx
    ret

.done:
    xor eax, eax
    pop ecx
    ret

; ============================================================================
; ata_select_drive - Select master (0) or slave (1) drive
; Input:
;   [ebp+8]  = drive (0 = primary master, 1 = primary slave,
;                     2 = secondary master, 3 = secondary slave)
;   [ebp+12] = LBA bits 24-27 (upper 4 bits of 28-bit LBA)
; Returns: EAX = 0 on success
; ============================================================================
global ata_select_drive
ata_select_drive:
    push ebp
    mov ebp, esp
    push edx
    push ecx                ; Save ECX - caller may be using it

    mov eax, [ebp+8]        ; drive
    mov ecx, [ebp+12]       ; LBA high 4 bits

    ; Determine base port and drive bit
    cmp eax, 2
    jge .secondary

    ; Primary controller
    mov dx, ATA_PRIMARY_DRIVE_HEAD
    test eax, 1             ; Check if slave
    jz .set_master
    jmp .set_slave

.secondary:
    ; Secondary controller
    mov dx, ATA_SECONDARY_DRIVE_HEAD
    test eax, 1             ; Check if slave
    jz .set_master

.set_slave:
    ; 0xF0 = 1111 0000 = LBA mode + slave
    mov al, 0xF0
    jmp .write_drive

.set_master:
    ; 0xE0 = 1110 0000 = LBA mode + master
    mov al, 0xE0

.write_drive:
    ; Add LBA bits 24-27
    and cl, 0x0F
    or al, cl

    out dx, al

    ; Wait for drive selection to take effect (400ns)
    sub dx, 7               ; Get back to base port
    call ata_delay

    xor eax, eax
    pop ecx                 ; Restore ECX
    pop edx
    pop ebp
    ret

; ============================================================================
; ata_read_sectors_pio - Read sectors using PIO mode
; Input:
;   [ebp+8]  = drive (0-3)
;   [ebp+12] = LBA (sector number)
;   [ebp+16] = count (number of sectors, max 256, 0 = 256)
;   [ebp+20] = buffer pointer
; Returns: EAX = sectors read, or -1 on error
; ============================================================================
global ata_read_sectors_pio
ata_read_sectors_pio:
    push ebp
    mov ebp, esp
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov eax, [ebp+8]        ; drive
    mov ebx, [ebp+12]       ; LBA
    mov ecx, [ebp+16]       ; count
    mov edi, [ebp+20]       ; buffer

    ; Determine base port
    cmp eax, 2
    jge .secondary_port
    mov dx, ATA_PRIMARY_STATUS
    jmp .got_port
.secondary_port:
    mov dx, ATA_SECONDARY_STATUS
.got_port:

    ; Wait for BSY to clear
    call ata_wait_bsy
    test eax, eax
    jnz .error_bsy

    ; Select drive with LBA bits 24-27
    mov eax, ebx
    shr eax, 24
    and eax, 0x0F
    push eax                ; LBA high bits
    push dword [ebp+8]      ; drive
    call ata_select_drive
    add esp, 8

    ; Determine base port again for register writes
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_regs
    mov dx, ATA_PRIMARY_SECCOUNT
    jmp .write_regs
.secondary_regs:
    mov dx, ATA_SECONDARY_SECCOUNT

.write_regs:
    ; Write sector count
    mov al, cl
    out dx, al

    ; Write LBA low byte
    inc dx                  ; LBA_LO
    mov eax, ebx
    out dx, al

    ; Write LBA mid byte
    inc dx                  ; LBA_MID
    mov eax, ebx
    shr eax, 8
    out dx, al

    ; Write LBA high byte
    inc dx                  ; LBA_HI
    mov eax, ebx
    shr eax, 16
    out dx, al

    ; Send READ SECTORS command
    add dx, 2               ; Skip drive select, go to command
    mov al, ATA_CMD_READ_SECTORS
    out dx, al

    ; Read sectors
    mov esi, ecx            ; Save sector count
    test esi, esi
    jnz .read_loop
    mov esi, 256            ; 0 means 256 sectors

.read_loop:
    ; Set DX to status port before calling ata_wait_drq
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_status_loop
    mov dx, ATA_PRIMARY_STATUS
    jmp .wait_drq_loop
.secondary_status_loop:
    mov dx, ATA_SECONDARY_STATUS

.wait_drq_loop:
    ; Wait for data ready
    call ata_wait_drq
    test eax, eax
    jnz .error_drq

    ; Read 256 words (512 bytes) from data port
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_data
    mov dx, ATA_PRIMARY_DATA
    jmp .read_data
.secondary_data:
    mov dx, ATA_SECONDARY_DATA

.read_data:
    cld                     ; Clear direction flag - CRITICAL for rep insw
    mov ecx, 256            ; 256 words = 512 bytes
    rep insw                ; Read words from port DX to ES:EDI

    dec esi
    jnz .read_loop

    ; Return number of sectors read
    mov eax, [ebp+16]
    test eax, eax
    jnz .done
    mov eax, 256
    jmp .done

.error_bsy:
    push eax
    mov al, 'B'
    call dbg_char
    mov al, '!'
    call dbg_char
    pop eax
    jmp .error_common

.error_drq:
    push eax
    mov al, 'D'
    call dbg_char
    mov al, '!'
    call dbg_char
    pop eax
    jmp .error_common

.error_common:
    mov eax, -1

.done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    pop ebp
    ret

; ============================================================================
; ata_write_sectors_pio - Write sectors using PIO mode
; Input:
;   [ebp+8]  = drive (0-3)
;   [ebp+12] = LBA (sector number)
;   [ebp+16] = count (number of sectors, max 256, 0 = 256)
;   [ebp+20] = buffer pointer
; Returns: EAX = sectors written, or -1 on error
; ============================================================================
global ata_write_sectors_pio
ata_write_sectors_pio:
    push ebp
    mov ebp, esp
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov eax, [ebp+8]        ; drive
    mov ebx, [ebp+12]       ; LBA
    mov ecx, [ebp+16]       ; count
    mov esi, [ebp+20]       ; buffer

    ; Determine base port
    cmp eax, 2
    jge .secondary_port
    mov dx, ATA_PRIMARY_STATUS
    jmp .got_port
.secondary_port:
    mov dx, ATA_SECONDARY_STATUS
.got_port:

    ; Wait for BSY to clear
    call ata_wait_bsy
    test eax, eax
    jnz .error

    ; Select drive with LBA bits 24-27
    mov eax, ebx
    shr eax, 24
    and eax, 0x0F
    push eax                ; LBA high bits
    push dword [ebp+8]      ; drive
    call ata_select_drive
    add esp, 8

    ; Determine base port for register writes
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_regs
    mov dx, ATA_PRIMARY_SECCOUNT
    jmp .write_regs
.secondary_regs:
    mov dx, ATA_SECONDARY_SECCOUNT

.write_regs:
    ; Write sector count
    mov al, cl
    out dx, al

    ; Write LBA low byte
    inc dx                  ; LBA_LO
    mov eax, ebx
    out dx, al

    ; Write LBA mid byte
    inc dx                  ; LBA_MID
    mov eax, ebx
    shr eax, 8
    out dx, al

    ; Write LBA high byte
    inc dx                  ; LBA_HI
    mov eax, ebx
    shr eax, 16
    out dx, al

    ; Send WRITE SECTORS command
    add dx, 2               ; Skip drive select, go to command
    mov al, ATA_CMD_WRITE_SECTORS
    out dx, al

    ; Write sectors
    mov edi, [ebp+16]       ; Save sector count
    test edi, edi
    jnz .write_loop
    mov edi, 256            ; 0 means 256 sectors

.write_loop:
    ; Wait for DRQ (drive ready for data)
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_status
    mov dx, ATA_PRIMARY_STATUS
    jmp .wait_drq
.secondary_status:
    mov dx, ATA_SECONDARY_STATUS

.wait_drq:
    call ata_wait_drq
    test eax, eax
    jnz .error

    ; Write 256 words (512 bytes) to data port
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_data
    mov dx, ATA_PRIMARY_DATA
    jmp .write_data
.secondary_data:
    mov dx, ATA_SECONDARY_DATA

.write_data:
    cld                     ; Clear direction flag - CRITICAL for rep outsw
    mov ecx, 256            ; 256 words = 512 bytes
    rep outsw               ; Write words from DS:ESI to port DX

    dec edi
    jnz .write_loop

    ; Flush cache
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_flush
    mov dx, ATA_PRIMARY_COMMAND
    jmp .flush
.secondary_flush:
    mov dx, ATA_SECONDARY_COMMAND

.flush:
    mov al, ATA_CMD_FLUSH_CACHE
    out dx, al

    ; Wait for flush to complete
    call ata_wait_bsy

    ; Return number of sectors written
    mov eax, [ebp+16]
    test eax, eax
    jnz .done
    mov eax, 256
    jmp .done

.error:
    mov eax, -1

.done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    pop ebp
    ret

; ============================================================================
; ata_identify - Send IDENTIFY command to get drive info
; Input: [ebp+8] = drive (0-3)
; Returns: EAX = 0 on success, -1 on error
;          ata_identify_buffer contains the 512-byte response
; ============================================================================
global ata_identify
ata_identify:
    push ebp
    mov ebp, esp
    push ebx
    push ecx
    push edx
    push edi

    mov eax, [ebp+8]        ; drive

    ; Determine base port
    cmp eax, 2
    jge .secondary_port
    mov dx, ATA_PRIMARY_STATUS
    jmp .got_port
.secondary_port:
    mov dx, ATA_SECONDARY_STATUS
.got_port:

    ; Wait for BSY to clear
    call ata_wait_bsy
    test eax, eax
    jnz .error

    ; Select drive
    push dword 0            ; LBA high bits = 0
    push dword [ebp+8]      ; drive
    call ata_select_drive
    add esp, 8

    ; Clear sector count, LBA registers
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_regs
    mov dx, ATA_PRIMARY_SECCOUNT
    jmp .write_regs
.secondary_regs:
    mov dx, ATA_SECONDARY_SECCOUNT

.write_regs:
    xor al, al
    out dx, al              ; Sector count = 0
    inc dx
    out dx, al              ; LBA low = 0
    inc dx
    out dx, al              ; LBA mid = 0
    inc dx
    out dx, al              ; LBA high = 0

    ; Send IDENTIFY command
    add dx, 2               ; Command register
    mov al, ATA_CMD_IDENTIFY
    out dx, al

    ; Read status
    in al, dx
    test al, al
    jz .no_drive            ; Status 0 = no drive

    ; Wait for BSY to clear
    mov eax, [ebp+8]
    cmp eax, 2
    jge .id_sec_status
    mov dx, ATA_PRIMARY_STATUS
    jmp .id_wait_bsy2
.id_sec_status:
    mov dx, ATA_SECONDARY_STATUS
.id_wait_bsy2:
    call ata_wait_bsy
    test eax, eax
    jnz .error

    ; Check for ATAPI (LBA_MID and LBA_HI non-zero)
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_check
    mov dx, ATA_PRIMARY_LBA_MID
    jmp .check_atapi
.secondary_check:
    mov dx, ATA_SECONDARY_LBA_MID

.check_atapi:
    in al, dx
    test al, al
    jnz .no_drive           ; ATAPI device, not ATA
    inc dx
    in al, dx
    test al, al
    jnz .no_drive           ; ATAPI device, not ATA

    ; Wait for DRQ
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_drq
    mov dx, ATA_PRIMARY_STATUS
    jmp .wait_drq
.secondary_drq:
    mov dx, ATA_SECONDARY_STATUS

.wait_drq:
    call ata_wait_drq
    test eax, eax
    jnz .error

    ; Read 256 words into identify buffer
    mov edi, ata_identify_buffer
    mov eax, [ebp+8]
    cmp eax, 2
    jge .secondary_data
    mov dx, ATA_PRIMARY_DATA
    jmp .read_data
.secondary_data:
    mov dx, ATA_SECONDARY_DATA

.read_data:
    ; Clear direction flag (forward copy) - CRITICAL for rep insw
    cld

    ; Read 256 words (512 bytes) from data port
    mov ecx, 256
    rep insw

    xor eax, eax
    jmp .done

.no_drive:
    mov eax, -1
    jmp .done

.error:
    mov eax, -1

.done:
    pop edi
    pop edx
    pop ecx
    pop ebx
    pop ebp
    ret

; ============================================================================
; ata_irq14_handler - Primary ATA interrupt handler
; Called from IRQ handler in isr.asm
; ============================================================================
global ata_irq14_handler
ata_irq14_handler:
    push eax
    push edx

    ; Read status to clear interrupt
    mov dx, ATA_PRIMARY_STATUS
    in al, dx

    ; Set flag
    mov dword [ata_primary_irq_fired], 1

    pop edx
    pop eax
    ret

; ============================================================================
; ata_irq15_handler - Secondary ATA interrupt handler
; Called from IRQ handler in isr.asm
; ============================================================================
global ata_irq15_handler
ata_irq15_handler:
    push eax
    push edx

    ; Read status to clear interrupt
    mov dx, ATA_SECONDARY_STATUS
    in al, dx

    ; Set flag
    mov dword [ata_secondary_irq_fired], 1

    pop edx
    pop eax
    ret

; ============================================================================
; ata_get_identify_buffer - Return pointer to identify buffer
; Returns: EAX = pointer to 512-byte identify buffer
; ============================================================================
global ata_get_identify_buffer
ata_get_identify_buffer:
    mov eax, ata_identify_buffer
    ret

; ============================================================================
; ata_soft_reset - Software reset the ATA controller
; Input: [ebp+8] = controller (0 = primary, 1 = secondary)
; ============================================================================
global ata_soft_reset
ata_soft_reset:
    push ebp
    mov ebp, esp
    push eax
    push edx

    mov eax, [ebp+8]
    test eax, eax
    jnz .secondary

    mov dx, ATA_PRIMARY_CONTROL
    jmp .reset

.secondary:
    mov dx, ATA_SECONDARY_CONTROL

.reset:
    ; Set SRST bit (bit 2) + nIEN bit (bit 1) to disable interrupts
    mov al, 0x06
    out dx, al

    ; Wait 5us minimum
    push dx
    mov dx, 0x1F0
    call ata_delay
    call ata_delay
    call ata_delay
    call ata_delay
    call ata_delay
    pop dx

    ; Clear SRST, keep nIEN=1 (interrupts disabled for PIO mode)
    mov al, 0x02
    out dx, al

    ; Wait for drives to come back (up to 30 seconds per spec!)
    ; We'll wait a reasonable 2 seconds (2000 iterations of 1ms)
    mov ecx, 2000
.wait:
    push dx
    mov dx, 0x1F0
    call ata_delay
    call ata_delay
    call ata_delay
    call ata_delay
    pop dx
    dec ecx
    jnz .wait

    ; Keep nIEN=1 for PIO polling mode - don't enable interrupts
    ; mov al, 0x02  ; already set
    ; out dx, al

    pop edx
    pop eax
    pop ebp
    ret
