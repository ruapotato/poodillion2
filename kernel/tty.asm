; tty.asm - TTY/PTY subsystem for BrainhairOS
; Implements terminal line discipline and pseudo-terminals

bits 32

; TTY flags (c_lflag equivalent)
TTY_ECHO    equ 0x0001      ; Echo input characters
TTY_ICANON  equ 0x0002      ; Canonical mode (line editing)
TTY_ISIG    equ 0x0004      ; Enable signals (^C, ^Z, etc.)
TTY_ICRNL   equ 0x0008      ; Translate CR to NL on input
TTY_ONLCR   equ 0x0010      ; Translate NL to CR-NL on output

; Control characters
CTRL_C      equ 3           ; ^C - interrupt (SIGINT)
CTRL_D      equ 4           ; ^D - EOF
CTRL_H      equ 8           ; ^H - backspace
CTRL_U      equ 21          ; ^U - kill line
CTRL_W      equ 23          ; ^W - delete word
CTRL_Z      equ 26          ; ^Z - suspend (SIGSTOP)
CTRL_BACK   equ 127         ; DEL - backspace

; TTY structure (128 bytes per TTY)
; Offset  Size  Field
; 0       4     Flags (echo, canon, isig, etc.)
; 4       4     Foreground process group (PID)
; 8       4     Input buffer pointer
; 12      4     Input buffer size
; 16      4     Input buffer head (write position)
; 20      4     Input buffer tail (read position)
; 24      4     Line buffer pointer (for canonical mode)
; 28      4     Line buffer position
; 32      4     Read function pointer
; 36      4     Write function pointer
; 40      4     Output buffer pointer (optional)
; 44      4     Control terminal PID (session leader)
; 48      4     Window rows
; 52      4     Window cols
; 56      72    Reserved

TTY_SIZE    equ 128
MAX_TTYS    equ 8

; Line buffer size for canonical mode
LINE_BUF_SIZE   equ 256
INPUT_BUF_SIZE  equ 1024

; Signal numbers (from signal.asm)
SIGINT      equ 2
SIGTSTP     equ 20

; External references
extern serial_putchar
extern serial_getchar
extern serial_available
extern sys_kill
extern current_pid

section .data

; Number of allocated TTYs
global tty_count
tty_count:
    dd 0

; Current foreground TTY (for keyboard input)
global current_tty
current_tty:
    dd 0

section .bss

; TTY table
align 4
global tty_table
tty_table:
    resb TTY_SIZE * MAX_TTYS

; Input buffers for TTYs (1KB each)
align 4
tty_input_buffers:
    resb INPUT_BUF_SIZE * MAX_TTYS

; Line buffers for canonical mode (256 bytes each)
align 4
tty_line_buffers:
    resb LINE_BUF_SIZE * MAX_TTYS

section .text

; ============================================================================
; tty_init - Initialize TTY subsystem
; ============================================================================
global tty_init
tty_init:
    push eax
    push ecx
    push edi

    ; Clear TTY table
    mov edi, tty_table
    mov ecx, TTY_SIZE * MAX_TTYS / 4
    xor eax, eax
    rep stosd

    ; Clear input buffers
    mov edi, tty_input_buffers
    mov ecx, INPUT_BUF_SIZE * MAX_TTYS / 4
    rep stosd

    ; Clear line buffers
    mov edi, tty_line_buffers
    mov ecx, LINE_BUF_SIZE * MAX_TTYS / 4
    rep stosd

    mov dword [tty_count], 0
    mov dword [current_tty], 0

    ; Create default console TTY (tty0) on serial port
    push 0                      ; TTY index
    call tty_create_console
    add esp, 4

    pop edi
    pop ecx
    pop eax
    ret

; ============================================================================
; tty_create_console - Create a console TTY
; Input: [esp+4] = TTY index
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global tty_create_console
tty_create_console:
    push ebx
    push edi

    mov eax, [esp + 12]         ; TTY index
    cmp eax, MAX_TTYS
    jge .error

    ; Calculate TTY offset
    imul eax, TTY_SIZE
    add eax, tty_table
    mov edi, eax

    ; Set default flags: echo + canonical + signals + ICRNL + ONLCR
    mov dword [edi + 0], TTY_ECHO | TTY_ICANON | TTY_ISIG | TTY_ICRNL | TTY_ONLCR

    ; Set foreground process to 0 (kernel)
    mov dword [edi + 4], 0

    ; Set up input buffer
    mov eax, [esp + 12]         ; TTY index
    imul eax, INPUT_BUF_SIZE
    add eax, tty_input_buffers
    mov [edi + 8], eax          ; Input buffer pointer
    mov dword [edi + 12], INPUT_BUF_SIZE
    mov dword [edi + 16], 0     ; Head
    mov dword [edi + 20], 0     ; Tail

    ; Set up line buffer
    mov eax, [esp + 12]
    imul eax, LINE_BUF_SIZE
    add eax, tty_line_buffers
    mov [edi + 24], eax         ; Line buffer pointer
    mov dword [edi + 28], 0     ; Line position

    ; Set I/O functions (serial for console)
    mov dword [edi + 32], tty_serial_read
    mov dword [edi + 36], tty_serial_write

    ; Default window size (80x25)
    mov dword [edi + 48], 25    ; rows
    mov dword [edi + 52], 80    ; cols

    ; Increment TTY count
    inc dword [tty_count]

    xor eax, eax
    pop edi
    pop ebx
    ret

.error:
    mov eax, -1
    pop edi
    pop ebx
    ret

; ============================================================================
; tty_read - Read from TTY with line discipline
; Input:
;   [esp+4]  = TTY index
;   [esp+8]  = buffer pointer
;   [esp+12] = count
; Returns: EAX = bytes read, or -1 on error
; ============================================================================
global tty_read
tty_read:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov eax, [esp + 24]         ; TTY index
    cmp eax, MAX_TTYS
    jge .read_error

    ; Get TTY structure
    imul eax, TTY_SIZE
    add eax, tty_table
    mov esi, eax                ; ESI = TTY struct

    mov edi, [esp + 28]         ; Buffer
    mov ecx, [esp + 32]         ; Count
    xor edx, edx                ; Bytes read

    ; Check if canonical mode
    test dword [esi + 0], TTY_ICANON
    jnz .canonical_read

    ; Raw mode: read directly from input buffer
.raw_read:
    cmp edx, ecx
    jge .read_done

    ; Check if data in input buffer
    mov eax, [esi + 16]         ; head
    cmp eax, [esi + 20]         ; tail
    je .read_done               ; Buffer empty

    ; Read one byte from input buffer
    mov ebx, [esi + 8]          ; Input buffer
    mov eax, [esi + 20]         ; tail
    movzx eax, byte [ebx + eax]
    mov [edi + edx], al
    inc edx

    ; Advance tail
    mov eax, [esi + 20]
    inc eax
    cmp eax, [esi + 12]         ; Wrap around
    jl .no_wrap_raw
    xor eax, eax
.no_wrap_raw:
    mov [esi + 20], eax

    jmp .raw_read

.canonical_read:
    ; In canonical mode, wait for newline
    ; For now, read from line buffer if available

    ; Check if we have a complete line
    mov ebx, [esi + 24]         ; Line buffer
    mov eax, [esi + 28]         ; Line position

    ; If line position is 0, nothing to read
    test eax, eax
    jz .read_done

    ; Copy line buffer to user buffer
    xor edx, edx
.copy_line:
    cmp edx, ecx
    jge .line_done
    cmp edx, [esi + 28]
    jge .line_done

    mov al, [ebx + edx]
    mov [edi + edx], al
    inc edx

    ; Check for newline
    cmp al, 10
    je .line_done

    jmp .copy_line

.line_done:
    ; Clear consumed portion of line buffer
    push edx
    mov ecx, edx
    mov edi, ebx
    xor eax, eax
    rep stosb
    pop edx

    ; Reset line position if we consumed everything
    mov eax, edx
    cmp eax, [esi + 28]
    jl .partial_line
    mov dword [esi + 28], 0

.partial_line:

.read_done:
    mov eax, edx
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

.read_error:
    mov eax, -1
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; tty_write - Write to TTY with output processing
; Input:
;   [esp+4]  = TTY index
;   [esp+8]  = buffer pointer
;   [esp+12] = count
; Returns: EAX = bytes written, or -1 on error
; ============================================================================
global tty_write
tty_write:
    push ebx
    push ecx
    push esi
    push edi

    mov eax, [esp + 20]         ; TTY index
    cmp eax, MAX_TTYS
    jge .write_error

    ; Get TTY structure
    imul eax, TTY_SIZE
    add eax, tty_table
    mov edi, eax                ; EDI = TTY struct

    mov esi, [esp + 24]         ; Buffer
    mov ecx, [esp + 28]         ; Count
    xor ebx, ebx                ; Bytes written

    test ecx, ecx
    jz .write_done

.write_loop:
    ; Get byte
    movzx eax, byte [esi + ebx]

    ; Check for NL -> CR-NL translation
    test dword [edi + 0], TTY_ONLCR
    jz .no_onlcr

    cmp al, 10                  ; LF
    jne .no_onlcr

    ; Output CR first
    push eax
    push 13                     ; CR
    call serial_putchar
    add esp, 4
    pop eax

.no_onlcr:
    ; Output the character
    push eax
    call serial_putchar
    add esp, 4

    inc ebx
    cmp ebx, ecx
    jl .write_loop

.write_done:
    mov eax, ebx
    pop edi
    pop esi
    pop ecx
    pop ebx
    ret

.write_error:
    mov eax, -1
    pop edi
    pop esi
    pop ecx
    pop ebx
    ret

; ============================================================================
; tty_input - Process keyboard input for TTY
; Input: [esp+4] = character
; Called from keyboard handler for each keypress
; ============================================================================
global tty_input
tty_input:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov eax, [current_tty]
    cmp eax, MAX_TTYS
    jge .input_done

    ; Get TTY structure
    imul eax, TTY_SIZE
    add eax, tty_table
    mov esi, eax                ; ESI = TTY struct

    mov eax, [esp + 24]         ; Input character
    mov edi, [esi + 24]         ; Line buffer
    mov ecx, [esi + 28]         ; Line position

    ; Check for signal characters if ISIG enabled
    test dword [esi + 0], TTY_ISIG
    jz .no_signals

    ; Check for ^C (SIGINT)
    cmp al, CTRL_C
    jne .not_sigint

    ; Send SIGINT to foreground process
    mov eax, [esi + 4]          ; Foreground PID
    test eax, eax
    jz .input_done              ; No foreground process

    push SIGINT
    push eax
    call sys_kill
    add esp, 8
    jmp .input_done

.not_sigint:
    ; Check for ^Z (SIGTSTP)
    cmp al, CTRL_Z
    jne .no_signals

    mov eax, [esi + 4]          ; Foreground PID
    test eax, eax
    jz .input_done

    push SIGTSTP
    push eax
    call sys_kill
    add esp, 8
    jmp .input_done

.no_signals:
    mov eax, [esp + 24]         ; Restore character

    ; Check for canonical mode
    test dword [esi + 0], TTY_ICANON
    jz .raw_input

    ; Canonical mode: line editing

    ; Check for backspace
    cmp al, CTRL_H
    je .do_backspace
    cmp al, CTRL_BACK
    je .do_backspace

    ; Check for ^U (kill line)
    cmp al, CTRL_U
    je .kill_line

    ; Check for CR -> NL translation
    test dword [esi + 0], TTY_ICRNL
    jz .no_icrnl
    cmp al, 13                  ; CR
    jne .no_icrnl
    mov al, 10                  ; Convert to NL
.no_icrnl:

    ; Normal character - add to line buffer
    cmp ecx, LINE_BUF_SIZE - 1
    jge .input_done             ; Line buffer full

    mov [edi + ecx], al
    inc ecx
    mov [esi + 28], ecx

    ; Echo if enabled
    test dword [esi + 0], TTY_ECHO
    jz .check_newline

    push eax
    call serial_putchar
    add esp, 4

.check_newline:
    ; Check if newline - if so, line is complete
    mov eax, [esp + 24]
    cmp al, 10
    jne .input_done

    ; Line complete - can be read now
    jmp .input_done

.do_backspace:
    test ecx, ecx
    jz .input_done              ; Nothing to delete

    dec ecx
    mov byte [edi + ecx], 0
    mov [esi + 28], ecx

    ; Echo backspace sequence (BS, space, BS)
    test dword [esi + 0], TTY_ECHO
    jz .input_done

    push 8
    call serial_putchar
    add esp, 4
    push 32
    call serial_putchar
    add esp, 4
    push 8
    call serial_putchar
    add esp, 4
    jmp .input_done

.kill_line:
    ; Erase entire line
    test dword [esi + 0], TTY_ECHO
    jz .clear_line

.erase_loop:
    test ecx, ecx
    jz .clear_line
    dec ecx
    push 8
    call serial_putchar
    add esp, 4
    push 32
    call serial_putchar
    add esp, 4
    push 8
    call serial_putchar
    add esp, 4
    jmp .erase_loop

.clear_line:
    mov dword [esi + 28], 0
    ; Clear line buffer
    mov edi, [esi + 24]
    mov ecx, LINE_BUF_SIZE / 4
    xor eax, eax
    rep stosd
    jmp .input_done

.raw_input:
    ; Raw mode: put directly in input buffer
    mov edi, [esi + 8]          ; Input buffer
    mov ecx, [esi + 16]         ; Head position

    ; Store character
    mov [edi + ecx], al

    ; Advance head
    inc ecx
    cmp ecx, [esi + 12]         ; Wrap around
    jl .no_wrap
    xor ecx, ecx
.no_wrap:
    mov [esi + 16], ecx

    ; Echo if enabled
    test dword [esi + 0], TTY_ECHO
    jz .input_done

    mov eax, [esp + 24]
    push eax
    call serial_putchar
    add esp, 4

.input_done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; tty_set_fg - Set foreground process for TTY
; Input:
;   [esp+4] = TTY index
;   [esp+8] = PID
; ============================================================================
global tty_set_fg
tty_set_fg:
    mov eax, [esp + 4]
    cmp eax, MAX_TTYS
    jge .setfg_done

    imul eax, TTY_SIZE
    add eax, tty_table
    mov ecx, [esp + 8]
    mov [eax + 4], ecx

.setfg_done:
    ret

; ============================================================================
; tty_get_fg - Get foreground process for TTY
; Input: [esp+4] = TTY index
; Returns: EAX = foreground PID
; ============================================================================
global tty_get_fg
tty_get_fg:
    mov eax, [esp + 4]
    cmp eax, MAX_TTYS
    jge .getfg_error

    imul eax, TTY_SIZE
    add eax, tty_table
    mov eax, [eax + 4]
    ret

.getfg_error:
    mov eax, -1
    ret

; ============================================================================
; tty_set_flags - Set TTY flags
; Input:
;   [esp+4] = TTY index
;   [esp+8] = flags
; ============================================================================
global tty_set_flags
tty_set_flags:
    mov eax, [esp + 4]
    cmp eax, MAX_TTYS
    jge .setflags_done

    imul eax, TTY_SIZE
    add eax, tty_table
    mov ecx, [esp + 8]
    mov [eax + 0], ecx

.setflags_done:
    ret

; ============================================================================
; tty_get_flags - Get TTY flags
; Input: [esp+4] = TTY index
; Returns: EAX = flags
; ============================================================================
global tty_get_flags
tty_get_flags:
    mov eax, [esp + 4]
    cmp eax, MAX_TTYS
    jge .getflags_error

    imul eax, TTY_SIZE
    add eax, tty_table
    mov eax, [eax + 0]
    ret

.getflags_error:
    xor eax, eax
    ret

; ============================================================================
; tty_get_winsize - Get window size
; Input:
;   [esp+4] = TTY index
;   [esp+8] = rows pointer
;   [esp+12] = cols pointer
; Returns: EAX = 0 on success
; ============================================================================
global tty_get_winsize
tty_get_winsize:
    push ebx

    mov eax, [esp + 8]
    cmp eax, MAX_TTYS
    jge .winsize_error

    imul eax, TTY_SIZE
    add eax, tty_table

    mov ebx, [esp + 12]         ; rows pointer
    test ebx, ebx
    jz .no_rows
    mov ecx, [eax + 48]
    mov [ebx], ecx

.no_rows:
    mov ebx, [esp + 16]         ; cols pointer
    test ebx, ebx
    jz .no_cols
    mov ecx, [eax + 52]
    mov [ebx], ecx

.no_cols:
    xor eax, eax
    pop ebx
    ret

.winsize_error:
    mov eax, -1
    pop ebx
    ret

; ============================================================================
; Serial I/O stubs for console TTY
; ============================================================================
tty_serial_read:
    ; Just return 0 for now - actual reading handled by tty_input
    xor eax, eax
    ret

tty_serial_write:
    ; Forward to serial_putchar
    push esi
    push ecx

    mov esi, [esp + 12]         ; buf
    mov ecx, [esp + 16]         ; count
    xor eax, eax

    test ecx, ecx
    jz .serial_write_done

.serial_write_loop:
    push eax
    movzx eax, byte [esi]
    push eax
    call serial_putchar
    add esp, 4
    pop eax
    inc esi
    inc eax
    cmp eax, ecx
    jl .serial_write_loop

.serial_write_done:
    pop ecx
    pop esi
    ret
