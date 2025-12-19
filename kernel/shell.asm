; Interactive Shell for BrainhairOS
; Provides command-line interface with basic Unix-like commands

bits 32

extern vga_init
extern vga_clear
extern vga_print
extern vga_putchar
extern vga_set_color
extern keyboard_init
extern keyboard_get_char
extern serial_init
extern serial_print

global shell_main
global shell_run

section .data
    ; Boot banner
    banner db 10, "========================================", 10
           db "  BrainhairOS v0.1 - Interactive Shell", 10
           db "========================================", 10, 10
           db "Type 'help' for available commands", 10, 10, 0

    ; Shell prompt
    prompt db "root@brainhair:~# ", 0

    ; Command buffer (max 80 characters)
    cmd_buffer times 81 db 0
    cmd_len db 0

    ; Commands and help text
    msg_help db "Available commands:", 10
             db "  help    - Show this help message", 10
             db "  clear   - Clear the screen", 10
             db "  echo    - Print text to screen", 10
             db "  uname   - Show system information", 10
             db "  uptime  - Show system uptime", 10
             db "  ps      - List processes", 10
             db "  ls      - List files (demo)", 10
             db "  cat     - Display file contents (demo)", 10, 0

    msg_uname db "BrainhairOS 0.1 i386", 10
              db "Kernel: Brainhair 0.1", 10
              db "Built: 2025-10-16", 10, 0

    msg_uptime db "System uptime: Just booted!", 10, 0

    msg_ps db " PID  CMD", 10
           db "   1  init", 10
           db "   2  shell", 10, 0

    msg_ls db "bin/  home/  root/  usr/  tmp/", 10, 0

    msg_cat db "File not found. Try: cat readme.txt", 10, 0

    msg_unknown db "Unknown command. Type 'help' for available commands.", 10, 0

    msg_echo_help db "Usage: echo [text]", 10, 0

    ; Command strings for comparison
    cmd_help db "help", 0
    cmd_clear db "clear", 0
    cmd_echo db "echo", 0
    cmd_uname db "uname", 0
    cmd_uptime db "uptime", 0
    cmd_ps db "ps", 0
    cmd_ls db "ls", 0
    cmd_cat db "cat", 0

section .text

; Main shell entry point
; This is called from the kernel wrapper
shell_main:
    ; Initialize hardware
    call serial_init
    call vga_init
    call keyboard_init

    ; Print banner to serial
    mov esi, banner
    call serial_print

    ; Print banner to VGA
    mov esi, banner
    call vga_print

    ; Run shell loop
    call shell_run

    ; Halt
.halt:
    hlt
    jmp .halt

; Main shell loop
shell_run:
    push eax
    push ebx
    push ecx
    push edx

.main_loop:
    ; Print prompt
    mov esi, prompt
    call vga_print
    mov esi, prompt
    call serial_print

    ; Read command
    call shell_read_line

    ; Skip empty commands
    mov al, [cmd_len]
    test al, al
    jz .main_loop

    ; Parse and execute command
    call shell_execute

    ; Loop forever
    jmp .main_loop

    pop edx
    pop ecx
    pop ebx
    pop eax
    ret

; Read a line of input from keyboard
; Stores result in cmd_buffer, length in cmd_len
shell_read_line:
    push eax
    push ebx

    ; Reset buffer
    mov byte [cmd_len], 0
    mov edi, cmd_buffer

.read_loop:
    ; Get character from keyboard
    call keyboard_get_char

    ; Check for special keys
    test al, al
    jz .read_loop           ; Ignore null (special keys we don't handle)

    cmp al, 13              ; Enter
    je .done

    cmp al, 8               ; Backspace
    je .backspace

    ; Regular character
    ; Check if buffer is full
    mov bl, [cmd_len]
    cmp bl, 80
    jge .read_loop          ; Buffer full, ignore

    ; Add to buffer
    mov [edi], al
    inc edi
    inc byte [cmd_len]

    ; Echo character
    call vga_putchar
    push eax
    mov [esp], eax          ; Keep char on stack
    ; Also print to serial (TODO)
    pop eax

    jmp .read_loop

.backspace:
    ; Check if buffer is empty
    mov bl, [cmd_len]
    test bl, bl
    jz .read_loop

    ; Remove character from buffer
    dec edi
    dec byte [cmd_len]

    ; Echo backspace to screen
    mov al, 8
    call vga_putchar

    jmp .read_loop

.done:
    ; Null-terminate buffer
    mov byte [edi], 0

    ; Print newline
    mov al, 10
    call vga_putchar

    pop ebx
    pop eax
    ret

; Execute command in cmd_buffer
shell_execute:
    push eax
    push esi
    push edi

    ; Compare with known commands
    mov esi, cmd_buffer

    ; Check for "help"
    mov edi, cmd_help
    call shell_strcmp
    test eax, eax
    jz .cmd_help_handler

    ; Check for "clear"
    mov edi, cmd_clear
    call shell_strcmp
    test eax, eax
    jz .cmd_clear_handler

    ; Check for "echo"
    mov esi, cmd_buffer
    mov edi, cmd_echo
    mov ecx, 4
    call shell_strncmp
    test eax, eax
    jz .cmd_echo_handler

    ; Check for "uname"
    mov esi, cmd_buffer
    mov edi, cmd_uname
    call shell_strcmp
    test eax, eax
    jz .cmd_uname_handler

    ; Check for "uptime"
    mov esi, cmd_buffer
    mov edi, cmd_uptime
    call shell_strcmp
    test eax, eax
    jz .cmd_uptime_handler

    ; Check for "ps"
    mov esi, cmd_buffer
    mov edi, cmd_ps
    call shell_strcmp
    test eax, eax
    jz .cmd_ps_handler

    ; Check for "ls"
    mov esi, cmd_buffer
    mov edi, cmd_ls
    call shell_strcmp
    test eax, eax
    jz .cmd_ls_handler

    ; Check for "cat"
    mov esi, cmd_buffer
    mov edi, cmd_cat
    mov ecx, 3
    call shell_strncmp
    test eax, eax
    jz .cmd_cat_handler

    ; Unknown command
    mov esi, msg_unknown
    call vga_print
    jmp .done

.cmd_help_handler:
    mov esi, msg_help
    call vga_print
    jmp .done

.cmd_clear_handler:
    call vga_clear
    jmp .done

.cmd_echo_handler:
    ; Skip "echo " (5 characters)
    mov esi, cmd_buffer
    add esi, 4
    ; Skip spaces
.echo_skip_spaces:
    lodsb
    cmp al, ' '
    je .echo_skip_spaces
    test al, al
    jz .echo_empty
    dec esi
    ; Print rest of line
    call vga_print
    mov al, 10
    call vga_putchar
    jmp .done
.echo_empty:
    mov al, 10
    call vga_putchar
    jmp .done

.cmd_uname_handler:
    mov esi, msg_uname
    call vga_print
    jmp .done

.cmd_uptime_handler:
    mov esi, msg_uptime
    call vga_print
    jmp .done

.cmd_ps_handler:
    mov esi, msg_ps
    call vga_print
    jmp .done

.cmd_ls_handler:
    mov esi, msg_ls
    call vga_print
    jmp .done

.cmd_cat_handler:
    mov esi, msg_cat
    call vga_print
    jmp .done

.done:
    pop edi
    pop esi
    pop eax
    ret

; Compare two null-terminated strings
; Parameters: ESI = string1, EDI = string2
; Returns: EAX = 0 if equal, non-zero otherwise
shell_strcmp:
    push ebx
    push esi
    push edi

.loop:
    mov al, [esi]
    mov bl, [edi]
    cmp al, bl
    jne .not_equal

    ; Check for end of string
    test al, al
    jz .equal

    inc esi
    inc edi
    jmp .loop

.equal:
    xor eax, eax
    jmp .done

.not_equal:
    mov eax, 1

.done:
    pop edi
    pop esi
    pop ebx
    ret

; Compare first N characters of two strings
; Parameters: ESI = string1, EDI = string2, ECX = count
; Returns: EAX = 0 if equal, non-zero otherwise
shell_strncmp:
    push ebx
    push esi
    push edi
    push ecx

.loop:
    test ecx, ecx
    jz .equal

    mov al, [esi]
    mov bl, [edi]
    cmp al, bl
    jne .not_equal

    inc esi
    inc edi
    dec ecx
    jmp .loop

.equal:
    xor eax, eax
    jmp .done

.not_equal:
    mov eax, 1

.done:
    pop ecx
    pop edi
    pop esi
    pop ebx
    ret
