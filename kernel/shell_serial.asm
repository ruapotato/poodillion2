; Serial-only shell wrapper for Mini-Nim
; Provides external functions that Mini-Nim can call

bits 32

extern serial_init
extern serial_print
extern serial_putchar

global kernel_main
global os_print
global os_putchar

section .data
    banner db 10, "========================================", 10
           db "  PoodillionOS v0.1 - Mini-Nim Shell", 10
           db "========================================", 10, 10
           db "Built with Mini-Nim compiler!", 10
           db "Commands: ls, cat, echo, help", 10, 10, 0

    prompt db "root@poodillion:~# ", 0

    msg_ls db "bin/  home/  root/  usr/  tmp/", 10, 0
    msg_cat db "Welcome to PoodillionOS!", 10
            db "A real operating system written in Mini-Nim", 10, 0
    msg_help db "Available commands:", 10
             db "  ls    - List files", 10
             db "  cat   - Display file", 10
             db "  echo  - Print text", 10
             db "  help  - Show this help", 10, 0

section .text

; Main kernel entry point
kernel_main:
    push ebp
    mov ebp, esp

    ; Initialize serial port
    call serial_init

    ; Print banner
    mov esi, banner
    call serial_print

    ; Demo: Print prompt and ls output
    mov esi, prompt
    call serial_print

    mov esi, msg_ls
    call serial_print

    ; Print prompt again
    mov al, 10
    call serial_putchar
    mov esi, prompt
    call serial_print

    ; Show help
    mov esi, msg_help
    call serial_print

    ; Print final prompt
    mov al, 10
    call serial_putchar
    mov esi, prompt
    call serial_print

    ; Halt
.halt:
    hlt
    jmp .halt

; External function for Mini-Nim: os_print(char* str)
; Prints a null-terminated string to serial port
os_print:
    push ebp
    mov ebp, esp
    push esi

    ; Get string pointer from stack (first argument)
    mov esi, [ebp + 8]
    call serial_print

    pop esi
    pop ebp
    ret

; External function for Mini-Nim: os_putchar(char c)
; Prints a single character to serial port
os_putchar:
    push ebp
    mov ebp, esp
    push eax

    ; Get character from stack (first argument)
    mov eax, [ebp + 8]
    call serial_putchar

    pop eax
    pop ebp
    ret
