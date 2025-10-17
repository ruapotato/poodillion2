; VGA Text Mode Driver for PoodillionOS
; Handles 80x25 color text display
; Base address: 0xB8000

bits 32

global vga_init
global vga_clear
global vga_putchar
global vga_print
global vga_set_color
global vga_get_cursor
global vga_set_cursor
global vga_scroll

section .data
    VGA_WIDTH   equ 80
    VGA_HEIGHT  equ 25
    VGA_SIZE    equ VGA_WIDTH * VGA_HEIGHT
    VGA_MEMORY  equ 0xB8000

    ; Cursor position
    cursor_x    db 0
    cursor_y    db 0

    ; Current color (default: light gray on black)
    current_color db 0x07

section .text

; Initialize VGA text mode
; Returns: void
vga_init:
    push eax
    push edi
    push ecx

    ; Clear the screen
    call vga_clear

    ; Reset cursor position
    mov byte [cursor_x], 0
    mov byte [cursor_y], 0

    pop ecx
    pop edi
    pop eax
    ret

; Clear the screen with current color
; Returns: void
vga_clear:
    push eax
    push edi
    push ecx

    ; Fill screen with spaces
    mov edi, VGA_MEMORY
    mov ah, [current_color]
    mov al, ' '
    mov ecx, VGA_SIZE
    rep stosw               ; Write AX to [EDI], increment EDI by 2

    ; Reset cursor
    mov byte [cursor_x], 0
    mov byte [cursor_y], 0

    pop ecx
    pop edi
    pop eax
    ret

; Set text color
; Parameters: AL = color (low nibble = foreground, high nibble = background)
; Returns: void
vga_set_color:
    mov [current_color], al
    ret

; Get cursor position
; Returns: DL = X, DH = Y
vga_get_cursor:
    mov dl, [cursor_x]
    mov dh, [cursor_y]
    ret

; Set cursor position
; Parameters: DL = X, DH = Y
; Returns: void
vga_set_cursor:
    mov [cursor_x], dl
    mov [cursor_y], dh
    ret

; Scroll screen up by one line
; Returns: void
vga_scroll:
    push eax
    push esi
    push edi
    push ecx

    ; Copy lines 1-24 to lines 0-23
    mov esi, VGA_MEMORY + (VGA_WIDTH * 2)    ; Source: line 1
    mov edi, VGA_MEMORY                       ; Dest: line 0
    mov ecx, VGA_WIDTH * (VGA_HEIGHT - 1)     ; Copy 24 lines
    rep movsw

    ; Clear last line
    mov edi, VGA_MEMORY + (VGA_WIDTH * (VGA_HEIGHT - 1) * 2)
    mov ah, [current_color]
    mov al, ' '
    mov ecx, VGA_WIDTH
    rep stosw

    pop ecx
    pop edi
    pop esi
    pop eax
    ret

; Put a character at current cursor position
; Parameters: AL = character to print
; Returns: void
vga_putchar:
    push eax
    push ebx
    push edx
    push edi

    ; Handle special characters
    cmp al, 10              ; Newline (\n)
    je .newline
    cmp al, 13              ; Carriage return (\r)
    je .carriage_return
    cmp al, 8               ; Backspace
    je .backspace
    cmp al, 9               ; Tab
    je .tab

    ; Regular character - print it
    jmp .print_char

.newline:
    ; Move to next line
    mov byte [cursor_x], 0
    mov al, [cursor_y]
    inc al
    mov [cursor_y], al

    ; Check if we need to scroll
    cmp al, VGA_HEIGHT
    jl .done

    ; Scroll and adjust cursor
    call vga_scroll
    mov byte [cursor_y], VGA_HEIGHT - 1
    jmp .done

.carriage_return:
    mov byte [cursor_x], 0
    jmp .done

.backspace:
    ; Move cursor back if not at start
    mov al, [cursor_x]
    test al, al
    jz .done                ; At start of line, do nothing
    dec al
    mov [cursor_x], al

    ; Erase character at cursor
    call .calculate_offset
    mov ah, [current_color]
    mov al, ' '
    mov [edi], ax
    jmp .done

.tab:
    ; Tab = 4 spaces
    mov al, [cursor_x]
    add al, 4
    and al, 0xFC            ; Align to multiple of 4
    cmp al, VGA_WIDTH
    jl .tab_ok
    mov al, VGA_WIDTH - 1
.tab_ok:
    mov [cursor_x], al
    jmp .done

.print_char:
    ; Calculate offset: (y * 80 + x) * 2
    call .calculate_offset

    ; Write character and color
    mov ah, [current_color]
    mov [edi], ax

    ; Advance cursor
    mov al, [cursor_x]
    inc al
    cmp al, VGA_WIDTH
    jl .no_wrap

    ; Wrap to next line
    mov byte [cursor_x], 0
    mov al, [cursor_y]
    inc al
    mov [cursor_y], al

    ; Check if we need to scroll
    cmp al, VGA_HEIGHT
    jl .done
    call vga_scroll
    mov byte [cursor_y], VGA_HEIGHT - 1
    jmp .done

.no_wrap:
    mov [cursor_x], al

.done:
    pop edi
    pop edx
    pop ebx
    pop eax
    ret

.calculate_offset:
    ; Calculate VGA memory offset
    ; Returns: EDI = VGA_MEMORY + (y * 80 + x) * 2
    push eax
    push ebx

    movzx edi, byte [cursor_y]
    mov ebx, VGA_WIDTH
    imul edi, ebx                   ; y * 80
    movzx ebx, byte [cursor_x]
    add edi, ebx                    ; + x
    shl edi, 1                      ; * 2 (2 bytes per character)
    add edi, VGA_MEMORY

    pop ebx
    pop eax
    ret

; Print a null-terminated string
; Parameters: ESI = pointer to string
; Returns: void
vga_print:
    push eax
    push esi

.loop:
    lodsb                   ; Load byte from [ESI] into AL, increment ESI
    test al, al             ; Check for null terminator
    jz .done
    call vga_putchar
    jmp .loop

.done:
    pop esi
    pop eax
    ret

; Print a string with length
; Parameters: ESI = pointer to string, ECX = length
; Returns: void
vga_print_len:
    push eax
    push esi
    push ecx

.loop:
    test ecx, ecx
    jz .done
    lodsb
    call vga_putchar
    dec ecx
    jmp .loop

.done:
    pop ecx
    pop esi
    pop eax
    ret
