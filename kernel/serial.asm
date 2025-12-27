; Serial port driver for Brainhair kernel
; COM1 at port 0x3F8
bits 32

section .text

; Initialize serial port (COM1)
global serial_init
serial_init:
    push eax
    push edx

    ; Disable interrupts
    mov dx, 0x3F9
    mov al, 0x00
    out dx, al

    ; Enable DLAB (set baud rate divisor)
    mov dx, 0x3FB
    mov al, 0x80
    out dx, al

    ; Set divisor to 3 (lo byte) 38400 baud
    mov dx, 0x3F8
    mov al, 0x03
    out dx, al

    ; Set divisor to 0 (hi byte)
    mov dx, 0x3F9
    mov al, 0x00
    out dx, al

    ; 8 bits, no parity, one stop bit
    mov dx, 0x3FB
    mov al, 0x03
    out dx, al

    ; Enable FIFO, clear them, with 14-byte threshold
    mov dx, 0x3FA
    mov al, 0xC7
    out dx, al

    ; IRQs enabled, RTS/DSR set
    mov dx, 0x3FC
    mov al, 0x0B
    out dx, al

    pop edx
    pop eax
    ret

; Write a single character to serial port
; Character in AL
global serial_putchar
serial_putchar:
    push edx
    push eax

.wait:
    ; Wait for transmit buffer to be empty
    mov dx, 0x3FD
    in al, dx
    test al, 0x20
    jz .wait

    ; Write character
    pop eax
    mov dx, 0x3F8
    out dx, al

    pop edx
    ret

; Write a null-terminated string to serial port
; Address of string in EAX
global serial_print
serial_print:
    push ebx
    push eax
    mov ebx, eax

.loop:
    mov al, [ebx]
    test al, al
    jz .done

    push eax
    call serial_putchar
    add esp, 4

    inc ebx
    jmp .loop

.done:
    pop eax
    pop ebx
    ret

; ============================================================================
; Check if serial data is available
; Returns: EAX = 1 if data available, 0 otherwise
; ============================================================================
global serial_available
serial_available:
    push edx

    mov dx, 0x3FD           ; Line status register
    in al, dx
    and eax, 0x01           ; Check Data Ready bit

    pop edx
    ret

; ============================================================================
; Read a character from serial port (non-blocking)
; Returns: EAX = character read, or -1 if no data available
; ============================================================================
global serial_getchar
serial_getchar:
    push edx

    ; Check if data is available
    mov dx, 0x3FD           ; Line status register
    in al, dx
    test al, 0x01           ; Check Data Ready bit
    jz .no_data

    ; Read character
    mov dx, 0x3F8           ; Data register
    in al, dx
    and eax, 0xFF           ; Clear upper bits
    pop edx
    ret

.no_data:
    mov eax, -1             ; Return -1 if no data
    pop edx
    ret

; ============================================================================
; syscall2 - Invoke a syscall with 2 arguments
; Input:
;   [esp+4] = syscall number
;   [esp+8] = arg1
;   [esp+12] = arg2
; Returns: EAX = syscall return value
; ============================================================================
global syscall1
syscall1:
    push ebx

    mov eax, [esp + 8]      ; syscall number
    mov ebx, [esp + 12]     ; arg1

    int 0x42                ; Invoke syscall

    pop ebx
    ret

global syscall2
syscall2:
    push ebx
    push ecx

    mov eax, [esp + 12]     ; syscall number
    mov ebx, [esp + 16]     ; arg1
    mov ecx, [esp + 20]     ; arg2

    int 0x42                ; Invoke syscall

    pop ecx
    pop ebx
    ret
