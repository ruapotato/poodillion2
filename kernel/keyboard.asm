; PS/2 Keyboard Driver for PoodillionOS
; Handles PS/2 keyboard input via 8042 controller
; Port 0x60: Data port
; Port 0x64: Status/Command port

bits 32

global keyboard_init
global keyboard_wait_input
global keyboard_read_scancode
global keyboard_get_char

; Keyboard ports
KBD_DATA_PORT    equ 0x60
KBD_STATUS_PORT  equ 0x64
KBD_CMD_PORT     equ 0x64

; Status register bits
KBD_STAT_OBF     equ 0x01    ; Output buffer full
KBD_STAT_IBF     equ 0x02    ; Input buffer full

section .data
    ; Scancode to ASCII translation table (US keyboard, scan code set 1)
    ; This is a simplified version - only handles basic keys
    scancode_table:
        db 0,  27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 8    ; 0x00-0x0E (backspace=8)
        db 9, 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', 13       ; 0x0F-0x1C (enter=13, tab=9)
        db 0, 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", '`'           ; 0x1D-0x29 (ctrl, letters)
        db 0, '\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 0             ; 0x2A-0x36 (shift, letters)
        db '*', 0, ' '                                                               ; 0x37-0x39 (alt, space)

    ; Shifted characters (when shift is held)
    scancode_table_shift:
        db 0,  27, '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', 8
        db 9, 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', 13
        db 0, 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~'
        db 0, '|', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', 0
        db '*', 0, ' '

    ; Keyboard state
    shift_pressed db 0
    ctrl_pressed  db 0
    alt_pressed   db 0

section .text

; Initialize the keyboard controller
; Returns: void
keyboard_init:
    push eax

    ; Disable first PS/2 port
    mov al, 0xAD
    out KBD_CMD_PORT, al

    ; Flush output buffer
    in al, KBD_DATA_PORT

    ; Enable first PS/2 port
    mov al, 0xAE
    out KBD_CMD_PORT, al

    ; Enable interrupts (we'll poll for now)
    ; TODO: Set up keyboard IRQ later

    pop eax
    ret

; Wait for keyboard to be ready for input
; Returns: void
keyboard_wait_input:
    push eax
.wait:
    in al, KBD_STATUS_PORT
    test al, KBD_STAT_IBF    ; Test if input buffer is full
    jnz .wait                 ; If full, keep waiting
    pop eax
    ret

; Wait for keyboard output to be ready
; Returns: void
keyboard_wait_output:
    push eax
.wait:
    in al, KBD_STATUS_PORT
    test al, KBD_STAT_OBF    ; Test if output buffer is full
    jz .wait                  ; If empty, keep waiting
    pop eax
    ret

; Read a scancode from the keyboard (blocking)
; Returns: AL = scancode
keyboard_read_scancode:
    push ebx

    ; Wait for data to be available
    call keyboard_wait_output

    ; Read the scancode
    in al, KBD_DATA_PORT

    pop ebx
    ret

; Check if a key is available (non-blocking)
; Returns: EAX = 1 if key available, 0 otherwise
keyboard_has_key:
    push ebx
    xor eax, eax

    ; Check if output buffer has data
    in al, KBD_STATUS_PORT
    and al, KBD_STAT_OBF

    ; Convert to 1 or 0
    movzx eax, al

    pop ebx
    ret

; Get a character from the keyboard (blocking)
; Handles modifier keys and converts scancode to ASCII
; Returns: AL = ASCII character (or 0 for special keys)
keyboard_get_char:
    push ebx
    push ecx
    push edx

.read_key:
    ; Read scancode
    call keyboard_read_scancode
    mov bl, al              ; Save scancode in BL

    ; Check for release code (bit 7 set)
    test bl, 0x80
    jnz .key_released

    ; Key pressed
    ; Check for shift (0x2A = left shift, 0x36 = right shift)
    cmp bl, 0x2A
    je .shift_down
    cmp bl, 0x36
    je .shift_down

    ; Check for ctrl (0x1D)
    cmp bl, 0x1D
    je .ctrl_down

    ; Check for alt (0x38)
    cmp bl, 0x38
    je .alt_down

    ; Regular key - convert to ASCII
    jmp .convert_to_ascii

.key_released:
    ; Clear release bit
    and bl, 0x7F

    ; Check for shift release
    cmp bl, 0x2A
    je .shift_up
    cmp bl, 0x36
    je .shift_up

    ; Check for ctrl release
    cmp bl, 0x1D
    je .ctrl_up

    ; Check for alt release
    cmp bl, 0x38
    je .alt_up

    ; Ignore other release codes
    jmp .read_key

.shift_down:
    mov byte [shift_pressed], 1
    jmp .read_key

.shift_up:
    mov byte [shift_pressed], 0
    jmp .read_key

.ctrl_down:
    mov byte [ctrl_pressed], 1
    jmp .read_key

.ctrl_up:
    mov byte [ctrl_pressed], 0
    jmp .read_key

.alt_down:
    mov byte [alt_pressed], 1
    jmp .read_key

.alt_up:
    mov byte [alt_pressed], 0
    jmp .read_key

.convert_to_ascii:
    ; Check if scancode is in valid range (0-0x39)
    cmp bl, 0x39
    ja .invalid_key

    ; Get ASCII from table
    movzx ebx, bl           ; Zero-extend to 32-bit

    ; Check if shift is pressed
    mov al, [shift_pressed]
    test al, al
    jnz .use_shift_table

    ; Use normal table
    mov al, [scancode_table + ebx]
    jmp .done

.use_shift_table:
    mov al, [scancode_table_shift + ebx]
    jmp .done

.invalid_key:
    ; Return 0 for unhandled keys
    xor al, al
    jmp .done

.done:
    pop edx
    pop ecx
    pop ebx
    ret
