; isr.asm - Interrupt Service Routines for BrainhairOS
; Handles CPU exceptions, hardware IRQs, and syscalls

bits 32

section .data

; Exception names for debugging
exc_names:
    dd exc_0, exc_1, exc_2, exc_3, exc_4, exc_5, exc_6, exc_7
    dd exc_8, exc_9, exc_10, exc_11, exc_12, exc_13, exc_14, exc_15
    dd exc_16, exc_17, exc_18, exc_19, exc_20, exc_21

exc_0:  db "Divide by Zero", 0
exc_1:  db "Debug", 0
exc_2:  db "NMI", 0
exc_3:  db "Breakpoint", 0
exc_4:  db "Overflow", 0
exc_5:  db "Bound Range", 0
exc_6:  db "Invalid Opcode", 0
exc_7:  db "Device N/A", 0
exc_8:  db "Double Fault", 0
exc_9:  db "Coprocessor", 0
exc_10: db "Invalid TSS", 0
exc_11: db "Segment N/P", 0
exc_12: db "Stack Fault", 0
exc_13: db "GPF", 0
exc_14: db "Page Fault", 0
exc_15: db "Reserved", 0
exc_16: db "x87 FPU", 0
exc_17: db "Alignment", 0
exc_18: db "Machine Check", 0
exc_19: db "SIMD", 0
exc_20: db "Virtualization", 0
exc_21: db "Control Prot", 0

msg_exception: db "[EXCEPTION] ", 0
msg_irq:       db "[IRQ] ", 0
msg_syscall:   db "[SYSCALL] ", 0
msg_at:        db " at EIP=0x", 0
msg_newline:   db 10, 0

section .bss

; Current interrupt number (for handler)
current_int: resb 4

section .text

; VGA memory constants
VGA_MEMORY equ 0xB8000
VGA_WIDTH  equ 80
VGA_RED    equ 0x04        ; Red text on black
VGA_WHITE  equ 0x0F        ; White text on black

; ============================================================================
; Simple VGA output for exceptions (standalone, no external deps)
; ============================================================================

; vga_write_char - Write a character at position
; Input: al = char, ah = attribute, edi = position (row * 80 + col)
vga_write_char:
    push ebx
    mov ebx, VGA_MEMORY
    shl edi, 1              ; Each character is 2 bytes
    mov [ebx + edi], ax     ; Write char + attribute
    pop ebx
    ret

; vga_write_string - Write null-terminated string
; Input: esi = string pointer, edi = start position, ah = attribute
vga_write_string:
    push ebx
    push ecx
    mov ebx, VGA_MEMORY
.loop:
    lodsb                   ; Load char from [esi] into al
    test al, al             ; Check for null terminator
    jz .done
    mov ecx, edi
    shl ecx, 1
    mov [ebx + ecx], ax     ; Write char + attribute
    inc edi
    jmp .loop
.done:
    pop ecx
    pop ebx
    ret

; vga_write_hex - Write 32-bit hex value
; Input: eax = value, edi = position, ah = attribute (preserved)
vga_write_hex:
    push ebx
    push ecx
    push edx

    mov ecx, 8              ; 8 hex digits
    mov edx, eax            ; Save value
    add edi, 7              ; Start from rightmost digit

.hex_loop:
    mov eax, edx
    and eax, 0x0F           ; Get low nibble
    cmp al, 10
    jl .digit
    add al, 'A' - 10
    jmp .write
.digit:
    add al, '0'
.write:
    push edi
    mov ah, VGA_RED
    call vga_write_char
    pop edi
    dec edi
    shr edx, 4
    loop .hex_loop

    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; Macro to create exception handlers without error code
; ============================================================================
%macro ISR_NOERR 1
global isr_%1
isr_%1:
    cli
    push dword 0            ; Dummy error code
    push dword %1           ; Interrupt number
    jmp isr_common
%endmacro

; ============================================================================
; Macro to create exception handlers with error code
; ============================================================================
%macro ISR_ERR 1
global isr_%1
isr_%1:
    cli
    push dword %1           ; Interrupt number (error code already on stack)
    jmp isr_common
%endmacro

; ============================================================================
; Macro to create IRQ handlers
; ============================================================================
%macro IRQ 2
global irq_%1
irq_%1:
    cli
    push dword 0            ; Dummy error code
    push dword %2           ; Interrupt number (32 + IRQ number)
    jmp irq_common
%endmacro

; ============================================================================
; CPU Exception Handlers (0-21)
; ============================================================================

; Without error code
ISR_NOERR 0     ; Divide by zero
ISR_NOERR 1     ; Debug
ISR_NOERR 2     ; NMI
ISR_NOERR 3     ; Breakpoint
ISR_NOERR 4     ; Overflow
ISR_NOERR 5     ; Bound range exceeded
ISR_NOERR 6     ; Invalid opcode
ISR_NOERR 7     ; Device not available
ISR_ERR   8     ; Double fault (has error code)
ISR_NOERR 9     ; Coprocessor segment overrun
ISR_ERR   10    ; Invalid TSS (has error code)
ISR_ERR   11    ; Segment not present (has error code)
ISR_ERR   12    ; Stack segment fault (has error code)
ISR_ERR   13    ; General protection fault (has error code)
ISR_ERR   14    ; Page fault (has error code)
ISR_NOERR 15    ; Reserved
ISR_NOERR 16    ; x87 FPU error
ISR_ERR   17    ; Alignment check (has error code)
ISR_NOERR 18    ; Machine check
ISR_NOERR 19    ; SIMD floating point
ISR_NOERR 20    ; Virtualization exception
ISR_ERR   21    ; Control protection (has error code)

; ============================================================================
; Hardware IRQ Handlers (IRQ 0-15 -> Interrupts 32-47)
; ============================================================================

IRQ 0, 32       ; PIT timer
IRQ 1, 33       ; Keyboard
IRQ 2, 34       ; Cascade
IRQ 3, 35       ; COM2
IRQ 4, 36       ; COM1
IRQ 5, 37       ; LPT2
IRQ 6, 38       ; Floppy
IRQ 7, 39       ; LPT1/spurious
IRQ 8, 40       ; RTC
IRQ 9, 41       ; Free
IRQ 10, 42      ; Free
IRQ 11, 43      ; Free
IRQ 12, 44      ; PS/2 mouse
IRQ 13, 45      ; FPU
IRQ 14, 46      ; Primary ATA
IRQ 15, 47      ; Secondary ATA

; ============================================================================
; Common exception handler
; Stack at this point:
;   [esp+0]  = interrupt number
;   [esp+4]  = error code (or 0)
;   [esp+8]  = EIP (return address)
;   [esp+12] = CS
;   [esp+16] = EFLAGS
; ============================================================================
isr_common:
    ; Save all registers
    pusha
    push ds
    push es
    push fs
    push gs

    ; Load kernel data segment
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax

    ; Get interrupt number
    mov eax, [esp + 48]     ; Skip saved regs (32) + segment regs (16)
    mov [current_int], eax

    ; Display exception on line 20 of screen
    ; Format: "[EXCEPTION] <name> at EIP=0x<hex>"

    ; Write "[EXCEPTION] "
    mov esi, msg_exception
    mov edi, 20 * VGA_WIDTH ; Line 20
    mov ah, VGA_RED
    call vga_write_string

    ; Write exception name
    mov eax, [current_int]
    cmp eax, 22
    jge .skip_name
    mov esi, [exc_names + eax * 4]
    ; edi is already at correct position from previous write
    mov ah, VGA_RED
    call vga_write_string
.skip_name:

    ; Write " at EIP=0x"
    mov esi, msg_at
    mov ah, VGA_RED
    call vga_write_string

    ; Write EIP as hex
    mov eax, [esp + 48 + 8]  ; Get EIP from stack
    call vga_write_hex

    ; For now, halt on exception
    cli
    hlt

    ; Restore segment registers (never reached for now)
    pop gs
    pop fs
    pop es
    pop ds
    popa

    ; Clean up interrupt number and error code
    add esp, 8

    ; Return from interrupt
    iret

; ============================================================================
; Common IRQ handler
; ============================================================================
extern timer_tick
extern keyboard_handler
extern ata_irq14_handler
extern ata_irq15_handler

irq_common:
    ; Save all registers
    pusha
    push ds
    push es
    push fs
    push gs

    ; Load kernel data segment
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax

    ; Get interrupt number
    mov eax, [esp + 48]
    mov [current_int], eax

    ; Handle specific IRQs
    cmp eax, 32             ; IRQ 0 = Timer (interrupt 32)
    jne .not_timer
    call timer_tick
    jmp .send_eoi

.not_timer:
    cmp eax, 33             ; IRQ 1 = Keyboard (interrupt 33)
    jne .not_keyboard
    call keyboard_handler
    jmp .send_eoi

.not_keyboard:
    cmp eax, 46             ; IRQ 14 = Primary ATA (interrupt 46)
    jne .not_ata_primary
    call ata_irq14_handler
    jmp .send_eoi

.not_ata_primary:
    cmp eax, 47             ; IRQ 15 = Secondary ATA (interrupt 47)
    jne .not_ata_secondary
    call ata_irq15_handler
    jmp .send_eoi

.not_ata_secondary:
    ; Other IRQs - just acknowledge and return

.send_eoi:
    ; Send EOI to PIC
    mov eax, [current_int]
    cmp eax, 40             ; IRQ 8-15 (interrupts 40-47)?
    jl .master_only
    ; Send EOI to slave PIC
    mov al, 0x20
    out 0xA0, al
.master_only:
    ; Send EOI to master PIC
    mov al, 0x20
    out 0x20, al

    ; Restore segment registers
    pop gs
    pop fs
    pop es
    pop ds
    popa

    ; Clean up interrupt number and error code
    add esp, 8

    ; Return from interrupt
    iret

; ============================================================================
; Syscall handler (int 0x42)
; Calling convention:
;   EAX = syscall number
;   EBX = arg1
;   ECX = arg2
;   EDX = arg3
;   ESI = arg4
;   EDI = arg5
;   Return value in EAX
; ============================================================================

; IPC functions from ipc.asm
extern ipc_send
extern ipc_recv
extern ipc_call
extern ipc_reply

global isr_syscall
isr_syscall:
    cli

    ; Save all registers (we'll restore and modify EAX for return)
    push ebp
    push edi
    push esi
    push edx
    push ecx
    push ebx
    push eax            ; Save syscall number

    ; Load kernel data segment
    push ds
    push es
    mov ax, 0x10
    mov ds, ax
    mov es, ax

    ; Get syscall number (now in eax, also at [esp+8])
    mov eax, [esp + 8]

    ; Dispatch syscall
    cmp eax, 1          ; SYS_exit
    je .syscall_exit

    cmp eax, 3          ; SYS_read
    je .syscall_read

    cmp eax, 4          ; SYS_write
    je .syscall_write

    cmp eax, 5          ; SYS_getpid
    je .syscall_getpid

    cmp eax, 6          ; SYS_yield
    je .syscall_yield

    cmp eax, 7          ; SYS_close
    je .syscall_close

    cmp eax, 20         ; SYS_send
    je .syscall_send

    cmp eax, 21         ; SYS_recv
    je .syscall_recv

    cmp eax, 22         ; SYS_call
    je .syscall_call

    cmp eax, 23         ; SYS_reply
    je .syscall_reply

    cmp eax, 40         ; SYS_spawn
    je .syscall_spawn

    cmp eax, 41         ; SYS_wait
    je .syscall_wait

    cmp eax, 42         ; SYS_getppid
    je .syscall_getppid

    cmp eax, 43         ; SYS_waitpid
    je .syscall_waitpid

    cmp eax, 44         ; SYS_fork
    je .syscall_fork

    cmp eax, 45         ; SYS_pipe
    je .syscall_pipe

    cmp eax, 46         ; SYS_dup
    je .syscall_dup

    cmp eax, 47         ; SYS_dup2
    je .syscall_dup2

    ; Networking syscalls (50-57)
    cmp eax, 50         ; SYS_NET_LISTEN
    je .syscall_net_listen

    cmp eax, 51         ; SYS_NET_ACCEPT
    je .syscall_net_accept

    cmp eax, 52         ; SYS_NET_CONNECT
    je .syscall_net_connect

    cmp eax, 53         ; SYS_NET_SEND
    je .syscall_net_send

    cmp eax, 54         ; SYS_NET_RECV
    je .syscall_net_recv

    cmp eax, 55         ; SYS_NET_CLOSE
    je .syscall_net_close

    cmp eax, 56         ; SYS_NET_STATE
    je .syscall_net_state

    cmp eax, 57         ; SYS_NET_POLL
    je .syscall_net_poll

    cmp eax, 58         ; SYS_NET_HAS_DATA
    je .syscall_net_has_data

    ; Process execution syscall (59)
    cmp eax, 59         ; SYS_EXEC
    je .syscall_exec

    ; Signal syscalls (60-63)
    cmp eax, 60         ; SYS_KILL
    je .syscall_kill

    cmp eax, 61         ; SYS_SIGNAL
    je .syscall_signal

    cmp eax, 62         ; SYS_SIGPROCMASK
    je .syscall_sigprocmask

    cmp eax, 63         ; SYS_RAISE
    je .syscall_raise

    ; User/group syscalls (70-77)
    cmp eax, 70         ; SYS_GETUID
    je .syscall_getuid

    cmp eax, 71         ; SYS_GETGID
    je .syscall_getgid

    cmp eax, 72         ; SYS_GETEUID
    je .syscall_geteuid

    cmp eax, 73         ; SYS_GETEGID
    je .syscall_getegid

    cmp eax, 74         ; SYS_SETUID
    je .syscall_setuid

    cmp eax, 75         ; SYS_SETGID
    je .syscall_setgid

    cmp eax, 9          ; SYS_LINK
    je .syscall_link

    cmp eax, 10         ; SYS_UNLINK
    je .syscall_unlink

    ; Filesystem syscalls (88-89)
    cmp eax, 88         ; SYS_SYMLINK
    je .syscall_symlink

    cmp eax, 89         ; SYS_READLINK
    je .syscall_readlink

    cmp eax, 999        ; SYS_UPTIME
    je .syscall_uptime

    ; RTC syscalls (80-82)
    cmp eax, 80         ; SYS_RTC_GET_TIME
    je .syscall_rtc_get_time

    cmp eax, 81         ; SYS_RTC_TO_UNIX
    je .syscall_rtc_to_unix

    cmp eax, 82         ; SYS_FLOCK
    je .syscall_flock

    ; Thread syscalls (200-204)
    cmp eax, 200        ; SYS_THREAD_CREATE
    je .syscall_thread_create

    cmp eax, 201        ; SYS_THREAD_EXIT
    je .syscall_thread_exit

    cmp eax, 202        ; SYS_THREAD_YIELD
    je .syscall_thread_yield

    cmp eax, 203        ; SYS_GET_THREAD_ID
    je .syscall_get_thread_id

    cmp eax, 204        ; SYS_IS_THREAD
    je .syscall_is_thread

    cmp eax, 205        ; SYS_THREAD_JOIN
    je .syscall_thread_join

    cmp eax, 206        ; SYS_THREAD_DETACH
    je .syscall_thread_detach

    ; Unix domain socket syscalls (210-216)
    cmp eax, 210        ; SYS_UNIX_LISTEN
    je .syscall_unix_listen

    cmp eax, 211        ; SYS_UNIX_CONNECT
    je .syscall_unix_connect

    cmp eax, 212        ; SYS_UNIX_ACCEPT
    je .syscall_unix_accept

    cmp eax, 213        ; SYS_UNIX_SEND
    je .syscall_unix_send

    cmp eax, 214        ; SYS_UNIX_RECV
    je .syscall_unix_recv

    cmp eax, 215        ; SYS_UNIX_CLOSE
    je .syscall_unix_close

    cmp eax, 216        ; SYS_UNIX_HAS_DATA
    je .syscall_unix_has_data

    ; TLS syscalls (220-221)
    cmp eax, 220        ; SYS_SET_TLS
    je .syscall_set_tls

    cmp eax, 221        ; SYS_GET_TLS
    je .syscall_get_tls

    ; X25519 syscalls (240-241)
    cmp eax, 240        ; SYS_X25519_KEYGEN
    je .syscall_x25519_keygen

    cmp eax, 241        ; SYS_X25519_SHARED
    je .syscall_x25519_shared

    ; Futex syscalls (250-252)
    cmp eax, 250        ; SYS_FUTEX_WAIT
    je .syscall_futex_wait

    cmp eax, 251        ; SYS_FUTEX_WAKE
    je .syscall_futex_wake

    cmp eax, 252        ; SYS_FUTEX_REQUEUE
    je .syscall_futex_requeue

    ; SHA-512 syscalls (260-262)
    cmp eax, 260        ; SYS_SHA512_INIT
    je .syscall_sha512_init

    cmp eax, 261        ; SYS_SHA512_UPDATE
    je .syscall_sha512_update

    cmp eax, 262        ; SYS_SHA512_FINAL
    je .syscall_sha512_final

    ; Ed25519 syscalls (270-273)
    cmp eax, 270        ; SYS_ED25519_KEYGEN
    je .syscall_ed25519_keygen

    cmp eax, 271        ; SYS_ED25519_SIGN
    je .syscall_ed25519_sign

    cmp eax, 272        ; SYS_ED25519_VERIFY
    je .syscall_ed25519_verify

    ; Unknown syscall - return -1
    mov eax, -1
    jmp .syscall_done

.syscall_exit:
    ; exit(code) - terminate process
    ; EBX = exit code
    extern exit_process
    mov eax, [esp + 20]     ; EBX (exit code)
    push eax
    call exit_process
    ; exit_process never returns
    add esp, 4
    jmp .syscall_done

.syscall_getpid:
    ; getpid() - return current PID
    extern current_pid
    mov eax, [current_pid]
    jmp .syscall_done

.syscall_yield:
    ; yield() - schedule another process
    extern yield
    call yield
    xor eax, eax
    jmp .syscall_done

.syscall_send:
    ; send(dest_pid, msg_ptr)
    ; EBX = dest_pid, ECX = msg_ptr
    mov eax, [esp + 20]     ; EBX (dest_pid) is at offset 20
    mov ebx, [esp + 16]     ; ECX (msg_ptr) is at offset 16
    push ebx
    push eax
    call ipc_send
    add esp, 8
    jmp .syscall_done

.syscall_recv:
    ; recv(from_pid, buf_ptr)
    ; EBX = from_pid, ECX = buf_ptr
    mov eax, [esp + 20]     ; EBX (from_pid)
    mov ebx, [esp + 16]     ; ECX (buf_ptr)
    push ebx
    push eax
    call ipc_recv
    add esp, 8
    jmp .syscall_done

.syscall_call:
    ; call(dest_pid, req_ptr, reply_ptr)
    ; EBX = dest_pid, ECX = req_ptr, EDX = reply_ptr
    mov eax, [esp + 20]     ; EBX (dest_pid)
    mov ebx, [esp + 16]     ; ECX (req_ptr)
    mov ecx, [esp + 12]     ; EDX (reply_ptr)
    push ecx
    push ebx
    push eax
    call ipc_call
    add esp, 12
    jmp .syscall_done

.syscall_reply:
    ; reply(dest_pid, msg_ptr)
    ; EBX = dest_pid, ECX = msg_ptr
    mov eax, [esp + 20]     ; EBX (dest_pid)
    mov ebx, [esp + 16]     ; ECX (msg_ptr)
    push ebx
    push eax
    call ipc_reply
    add esp, 8
    jmp .syscall_done

.syscall_spawn:
    ; spawn(entry_point)
    ; EBX = entry point address
    ; Returns: PID of new process or -1 on error
    extern create_process
    mov eax, [esp + 20]     ; EBX (entry point)
    mov ebx, [current_pid]  ; Parent PID
    push ebx
    push eax
    call create_process
    add esp, 8
    jmp .syscall_done

.syscall_wait:
    ; wait() - wait for any child to exit
    ; Returns: PID of exited child, or -1 on error
    extern waitpid
    push 0                  ; status pointer = NULL
    push -1                 ; pid = -1 (any child)
    call waitpid
    add esp, 8
    jmp .syscall_done

.syscall_getppid:
    ; getppid() - get parent PID
    extern getppid
    call getppid
    jmp .syscall_done

.syscall_waitpid:
    ; waitpid(pid, status_ptr) - wait for specific child
    ; EBX = pid (-1 for any), ECX = status_ptr (may be NULL)
    mov eax, [esp + 20]     ; EBX (pid)
    mov ebx, [esp + 16]     ; ECX (status_ptr)
    push ebx
    push eax
    call waitpid
    add esp, 8
    jmp .syscall_done

.syscall_fork:
    ; fork() - create child process
    ; Returns: child PID to parent, 0 to child, -1 on error
    extern fork
    call fork
    jmp .syscall_done

.syscall_read:
    ; read(fd, buf, count) -> bytes_read
    ; EBX = fd, ECX = buf, EDX = count
    extern sys_read
    mov eax, [esp + 12]     ; EDX (count)
    push eax
    mov eax, [esp + 20]     ; ECX (buf)
    push eax
    mov eax, [esp + 28]     ; EBX (fd)
    push eax
    call sys_read
    add esp, 12
    jmp .syscall_done

.syscall_write:
    ; write(fd, buf, count) -> bytes_written
    ; EBX = fd, ECX = buf, EDX = count
    extern sys_write
    mov eax, [esp + 12]     ; EDX (count)
    push eax
    mov eax, [esp + 20]     ; ECX (buf)
    push eax
    mov eax, [esp + 28]     ; EBX (fd)
    push eax
    call sys_write
    add esp, 12
    jmp .syscall_done

.syscall_close:
    ; close(fd) -> 0/-1
    ; EBX = fd
    extern sys_close
    mov eax, [esp + 20]     ; EBX (fd)
    push eax
    call sys_close
    add esp, 4
    jmp .syscall_done

.syscall_pipe:
    ; pipe(fds) -> 0/-1
    ; EBX = pointer to int32[2]
    extern sys_pipe
    mov eax, [esp + 20]     ; EBX (fds pointer)
    push eax
    call sys_pipe
    add esp, 4
    jmp .syscall_done

.syscall_dup:
    ; dup(fd) -> new_fd
    ; EBX = fd
    extern sys_dup
    mov eax, [esp + 20]     ; EBX (fd)
    push eax
    call sys_dup
    add esp, 4
    jmp .syscall_done

.syscall_dup2:
    ; dup2(old_fd, new_fd) -> new_fd
    ; EBX = old_fd, ECX = new_fd
    extern sys_dup2
    mov eax, [esp + 16]     ; ECX (new_fd)
    push eax
    mov eax, [esp + 24]     ; EBX (old_fd)
    push eax
    call sys_dup2
    add esp, 8
    jmp .syscall_done

; ============= Networking syscalls =============

.syscall_net_listen:
    ; net_listen(port) -> conn
    ; EBX = port
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    extern tcp_listen
    mov eax, [esp + 12]     ; EBX (port)
    push eax
    call tcp_listen
    add esp, 4
    jmp .syscall_done

.syscall_net_accept:
    ; net_accept_ready(conn) -> 0/1
    ; EBX = conn
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    extern tcp_accept_ready
    mov eax, [esp + 12]     ; EBX (conn)
    push eax
    call tcp_accept_ready
    add esp, 4
    jmp .syscall_done

.syscall_net_connect:
    ; net_connect(ip_ptr, port) -> conn
    ; EBX = ip_ptr, ECX = port
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    extern tcp_connect
    mov eax, [esp + 12]     ; EBX (ip_ptr)
    mov ebx, [esp + 16]     ; ECX (port)
    push ebx                ; port
    push eax                ; ip_ptr
    call tcp_connect
    add esp, 8
    jmp .syscall_done

.syscall_net_send:
    ; net_send(conn, data, len) -> sent
    ; EBX = conn, ECX = data, EDX = len
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    extern tcp_write
    mov eax, [esp + 12]     ; EBX (conn)
    mov ebx, [esp + 16]     ; ECX (data)
    mov ecx, [esp + 20]     ; EDX (len)
    push ecx                ; len
    push ebx                ; data
    push eax                ; conn
    call tcp_write
    add esp, 12
    jmp .syscall_done

.syscall_net_recv:
    ; net_recv(conn, buf, max_len) -> read
    ; EBX = conn, ECX = buf, EDX = max_len
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    extern tcp_read
    mov eax, [esp + 12]     ; EBX (conn)
    mov ebx, [esp + 16]     ; ECX (buf)
    mov ecx, [esp + 20]     ; EDX (max_len)
    push ecx                ; max_len
    push ebx                ; buf
    push eax                ; conn
    call tcp_read
    add esp, 12
    jmp .syscall_done

.syscall_net_close:
    ; net_close(conn)
    ; EBX = conn
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    extern tcp_close
    mov eax, [esp + 12]     ; EBX (conn)
    push eax
    call tcp_close
    add esp, 4
    xor eax, eax            ; return 0
    jmp .syscall_done

.syscall_net_state:
    ; net_state(conn) -> state
    ; EBX = conn
    ; Stack: ES DS EAX EBX ECX EDX ESI EDI EBP EIP...
    ;        +0 +4 +8  +12 +16 +20 +24 +28 +32 +36
    ; Returns tcp_state[conn]
    extern tcp_state
    mov eax, [esp + 12]     ; EBX (conn)
    ; Bounds check: if conn >= 16, return -1
    cmp eax, 16
    jge .syscall_net_state_invalid
    ; Get tcp_state[conn] - array of int32 (4 bytes each)
    shl eax, 2              ; conn * 4
    add eax, tcp_state      ; &tcp_state[conn]
    mov eax, [eax]          ; tcp_state[conn]
    jmp .syscall_done
.syscall_net_state_invalid:
    mov eax, -1
    jmp .syscall_done

.syscall_net_poll:
    ; net_poll() - process network packets
    extern net_poll
    call net_poll
    xor eax, eax            ; return 0
    jmp .syscall_done

.syscall_net_has_data:
    ; net_has_data(conn) -> 1 if data ready, 0 otherwise
    ; EBX = conn
    ; Calls tcp_has_data(conn) function
    extern tcp_has_data
    mov eax, [esp + 12]     ; EBX (conn)
    push eax
    call tcp_has_data
    add esp, 4
    jmp .syscall_done

; ============= Signal syscalls =============

.syscall_kill:
    ; kill(pid, sig) -> 0/-1
    ; EBX = pid, ECX = sig
    extern sys_kill
    mov eax, [esp + 16]     ; ECX (sig)
    push eax
    mov eax, [esp + 24]     ; EBX (pid)
    push eax
    call sys_kill
    add esp, 8
    jmp .syscall_done

.syscall_signal:
    ; signal(sig, handler) -> old_handler
    ; EBX = sig, ECX = handler
    extern sys_signal
    mov eax, [esp + 16]     ; ECX (handler)
    push eax
    mov eax, [esp + 24]     ; EBX (sig)
    push eax
    call sys_signal
    add esp, 8
    jmp .syscall_done

.syscall_sigprocmask:
    ; sigprocmask(how, set, oldset) -> 0/-1
    ; EBX = how, ECX = set, EDX = oldset
    extern sys_sigprocmask
    mov eax, [esp + 12]     ; EDX (oldset)
    push eax
    mov eax, [esp + 20]     ; ECX (set)
    push eax
    mov eax, [esp + 28]     ; EBX (how)
    push eax
    call sys_sigprocmask
    add esp, 12
    jmp .syscall_done

.syscall_raise:
    ; raise(sig) -> 0
    ; EBX = sig
    extern sys_raise
    mov eax, [esp + 20]     ; EBX (sig)
    push eax
    call sys_raise
    add esp, 4
    jmp .syscall_done

.syscall_exec:
    ; exec(elf_ptr, argv) -> -1 on error, does not return on success
    ; EBX = pointer to ELF image in memory
    ; ECX = argument string pointer (can be 0)
    extern sys_exec
    mov eax, [esp + 16]     ; ECX (argv)
    push eax
    mov eax, [esp + 24]     ; EBX (elf_ptr)
    push eax
    call sys_exec
    add esp, 8
    ; If we get here, exec failed
    jmp .syscall_done

.syscall_getuid:
    ; getuid() -> UID
    extern sys_getuid
    call sys_getuid
    jmp .syscall_done

.syscall_getgid:
    ; getgid() -> GID
    extern sys_getgid
    call sys_getgid
    jmp .syscall_done

.syscall_geteuid:
    ; geteuid() -> EUID
    extern sys_geteuid
    call sys_geteuid
    jmp .syscall_done

.syscall_getegid:
    ; getegid() -> EGID
    extern sys_getegid
    call sys_getegid
    jmp .syscall_done

.syscall_setuid:
    ; setuid(uid) -> 0 or -1
    extern sys_setuid
    mov eax, [esp + 20]     ; EBX (uid)
    push eax
    call sys_setuid
    add esp, 4
    jmp .syscall_done

.syscall_setgid:
    ; setgid(gid) -> 0 or -1
    extern sys_setgid
    mov eax, [esp + 20]     ; EBX (gid)
    push eax
    call sys_setgid
    add esp, 4
    jmp .syscall_done

.syscall_link:
    ; link(target, linkname) -> 0 or -1
    ; EBX = target path, ECX = linkname path
    extern sys_link
    mov eax, [esp + 16]     ; ECX (linkname)
    push eax
    mov eax, [esp + 24]     ; EBX (target)
    push eax
    call sys_link
    add esp, 8
    jmp .syscall_done

.syscall_unlink:
    ; unlink(path) -> 0 or -1
    ; EBX = path
    extern sys_unlink
    mov eax, [esp + 20]     ; EBX (path)
    push eax
    call sys_unlink
    add esp, 4
    jmp .syscall_done

.syscall_symlink:
    ; symlink(target, linkpath) -> 0 or -1
    ; EBX = target path, ECX = linkpath
    extern sys_symlink
    mov eax, [esp + 16]     ; ECX (linkpath)
    push eax
    mov eax, [esp + 24]     ; EBX (target)
    push eax
    call sys_symlink
    add esp, 8
    jmp .syscall_done

.syscall_readlink:
    ; readlink(path, buf, bufsize) -> bytes or -1
    ; EBX = path, ECX = buf, EDX = bufsize
    extern sys_readlink
    mov eax, [esp + 12]     ; EDX (bufsize)
    push eax
    mov eax, [esp + 20]     ; ECX (buf)
    push eax
    mov eax, [esp + 28]     ; EBX (path)
    push eax
    call sys_readlink
    add esp, 12
    jmp .syscall_done

.syscall_uptime:
    ; uptime(uptime_ptr) -> 0
    ; EBX = pointer to uptime struct (int32 seconds, int32 milliseconds)
    ; Returns uptime in seconds and milliseconds
    extern get_tick_count
    call get_tick_count
    ; EAX now has tick count
    ; Convert to seconds: ticks / 18 (PIT timer runs at ~18.2 Hz)
    ; First, calculate seconds
    push edx
    xor edx, edx
    mov ecx, 18
    div ecx                 ; EAX = seconds, EDX = remainder ticks

    ; Store seconds
    mov ebx, [esp + 24]     ; Get uptime_ptr from stack (+4 for pushed edx)
    test ebx, ebx
    jz .uptime_null_ptr
    mov [ebx], eax          ; Store seconds

    ; Calculate milliseconds from remainder
    ; milliseconds = (remainder * 1000) / 18
    mov eax, edx            ; remainder ticks
    mov ecx, 1000
    mul ecx                 ; EDX:EAX = remainder * 1000
    mov ecx, 18
    div ecx                 ; EAX = milliseconds
    mov [ebx + 4], eax      ; Store milliseconds

.uptime_null_ptr:
    pop edx
    xor eax, eax            ; Return 0
    jmp .syscall_done

; ============= RTC syscalls =============

.syscall_rtc_get_time:
    ; rtc_get_time(time_ptr) -> 0 or -1
    ; EBX = pointer to time structure (6 bytes)
    extern rtc_get_time
    mov eax, [esp + 20]     ; EBX (time_ptr)
    push eax
    call rtc_get_time
    add esp, 4
    jmp .syscall_done

.syscall_rtc_to_unix:
    ; rtc_to_unix_timestamp() -> timestamp
    ; Returns Unix timestamp from RTC
    extern rtc_to_unix_timestamp
    call rtc_to_unix_timestamp
    jmp .syscall_done

.syscall_flock:
    ; flock(fd, operation) -> 0 or -1
    ; EBX = fd, ECX = operation (LOCK_SH, LOCK_EX, LOCK_UN, LOCK_NB)
    extern sys_flock
    mov eax, [esp + 16]     ; ECX (operation)
    push eax
    mov eax, [esp + 24]     ; EBX (fd)
    push eax
    call sys_flock
    add esp, 8
    jmp .syscall_done

; ============================================================================
; Thread Syscall Handlers (200-204)
; ============================================================================

.syscall_thread_create:
    ; thread_create(entry, arg) -> thread PID or -1
    ; EBX = entry point, ECX = user argument
    extern thread_create
    mov eax, [esp + 16]     ; ECX (user argument)
    push eax
    mov eax, [esp + 24]     ; EBX (entry point)
    push eax
    call thread_create
    add esp, 8
    jmp .syscall_done

.syscall_thread_exit:
    ; thread_exit(code) - exit current thread
    ; EBX = exit code
    extern thread_exit
    mov eax, [esp + 20]     ; EBX (exit code)
    push eax
    call thread_exit
    ; thread_exit doesn't return for threads
    add esp, 4
    jmp .syscall_done

.syscall_thread_yield:
    ; thread_yield() - yield to another thread/process
    extern thread_yield
    call thread_yield
    xor eax, eax
    jmp .syscall_done

.syscall_get_thread_id:
    ; get_thread_id() -> thread ID (0 for main process)
    extern get_thread_id
    call get_thread_id
    jmp .syscall_done

.syscall_is_thread:
    ; is_thread() -> 1 if thread, 0 if main process
    extern is_thread
    call is_thread
    jmp .syscall_done

.syscall_thread_join:
    ; thread_join(tid, status_ptr) -> 0 on success, -1 on error
    ; EBX = thread PID, ECX = status pointer
    extern thread_join
    mov eax, [esp + 16]     ; ECX (status pointer)
    push eax
    mov eax, [esp + 24]     ; EBX (thread PID)
    push eax
    call thread_join
    add esp, 8
    jmp .syscall_done

.syscall_thread_detach:
    ; thread_detach(tid) -> 0 on success, -1 on error
    ; EBX = thread PID
    extern thread_detach
    mov eax, [esp + 20]     ; EBX (thread PID)
    push eax
    call thread_detach
    add esp, 4
    jmp .syscall_done

; ============================================================================
; Thread-Local Storage Syscall Handlers (220-221)
; ============================================================================

.syscall_set_tls:
    ; set_tls(base) -> 0 on success
    ; EBX = TLS base address
    extern set_tls_base
    mov eax, [esp + 20]     ; EBX (base address)
    push eax
    call set_tls_base
    add esp, 4
    jmp .syscall_done

.syscall_get_tls:
    ; get_tls() -> TLS base address
    extern get_tls_base
    call get_tls_base
    jmp .syscall_done

; ============================================================================
; X25519 Key Exchange Syscall Handlers (240-241)
; ============================================================================

.syscall_x25519_keygen:
    ; x25519_keygen(public_key, private_key) -> 0 on success
    ; EBX = public key output pointer (32 bytes)
    ; ECX = private key input pointer (32 bytes)
    extern x25519_keygen
    mov eax, [esp + 20]     ; EBX (public key)
    mov ebx, [esp + 16]     ; ECX (private key)
    push ebx
    push eax
    call x25519_keygen
    add esp, 8
    xor eax, eax            ; Return 0 on success
    jmp .syscall_done

.syscall_x25519_shared:
    ; x25519_shared(shared, our_private, their_public) -> 0 on success
    ; EBX = shared secret output pointer (32 bytes)
    ; ECX = our private key pointer (32 bytes)
    ; EDX = their public key pointer (32 bytes)
    extern x25519_shared
    mov eax, [esp + 20]     ; EBX (shared output)
    mov ebx, [esp + 16]     ; ECX (our private)
    mov ecx, [esp + 12]     ; EDX (their public)
    push ecx
    push ebx
    push eax
    call x25519_shared
    add esp, 12
    xor eax, eax            ; Return 0 on success
    jmp .syscall_done

; ============================================================================
; Futex Syscall Handlers (250-252)
; ============================================================================

.syscall_futex_wait:
    ; futex_wait(addr, expected, timeout) -> 0 on success, -1 on value change
    ; EBX = address to wait on
    ; ECX = expected value
    ; EDX = timeout (0 = infinite)
    extern futex_wait
    mov eax, [esp + 20]     ; EBX (address)
    mov ebx, [esp + 16]     ; ECX (expected)
    mov ecx, [esp + 12]     ; EDX (timeout)
    push ecx
    push ebx
    push eax
    call futex_wait
    add esp, 12
    jmp .syscall_done

.syscall_futex_wake:
    ; futex_wake(addr, count) -> number woken
    ; EBX = address to wake on
    ; ECX = max number to wake (0 = all)
    extern futex_wake
    mov eax, [esp + 20]     ; EBX (address)
    mov ebx, [esp + 16]     ; ECX (count)
    push ebx
    push eax
    call futex_wake
    add esp, 8
    jmp .syscall_done

.syscall_futex_requeue:
    ; futex_requeue(src_addr, dst_addr, wake_count, requeue_count) -> total processed
    ; EBX = source address
    ; ECX = destination address
    ; EDX = max to wake
    ; ESI = max to requeue
    extern futex_requeue
    mov eax, [esp + 20]     ; EBX (src)
    mov ebx, [esp + 16]     ; ECX (dst)
    mov ecx, [esp + 12]     ; EDX (wake count)
    mov edx, [esp + 8]      ; ESI (requeue count)
    push edx
    push ecx
    push ebx
    push eax
    call futex_requeue
    add esp, 16
    jmp .syscall_done

; ============================================================================
; SHA-512 Syscall Handlers (260-262)
; ============================================================================

.syscall_sha512_init:
    ; sha512_init() -> 0
    extern sha512_init
    call sha512_init
    xor eax, eax
    jmp .syscall_done

.syscall_sha512_update:
    ; sha512_update(data, length) -> 0
    ; EBX = data pointer
    ; ECX = length
    extern sha512_update
    mov eax, [esp + 20]     ; EBX (data)
    mov ebx, [esp + 16]     ; ECX (length)
    push ebx
    push eax
    call sha512_update
    add esp, 8
    xor eax, eax
    jmp .syscall_done

.syscall_sha512_final:
    ; sha512_final(output) -> 0
    ; EBX = 64-byte output buffer
    extern sha512_final
    mov eax, [esp + 20]     ; EBX (output)
    push eax
    call sha512_final
    add esp, 4
    xor eax, eax
    jmp .syscall_done

; ============================================================================
; Ed25519 Syscall Handlers (270-273)
; ============================================================================

.syscall_ed25519_keygen:
    ; ed25519_keygen(seed, pubkey, privkey) -> 0 on success
    ; EBX = 32-byte seed
    ; ECX = 32-byte output public key
    ; EDX = 64-byte output private key
    extern ed25519_keygen
    mov eax, [esp + 20]     ; EBX (seed)
    mov ebx, [esp + 16]     ; ECX (pubkey)
    mov ecx, [esp + 12]     ; EDX (privkey)
    push ecx
    push ebx
    push eax
    call ed25519_keygen
    add esp, 12
    jmp .syscall_done

.syscall_ed25519_sign:
    ; ed25519_sign(msg, msg_len, privkey, sig) -> 0 on success
    ; EBX = message pointer
    ; ECX = message length
    ; EDX = 64-byte private key
    ; ESI = 64-byte output signature
    extern ed25519_sign
    mov eax, [esp + 20]     ; EBX (msg)
    mov ebx, [esp + 16]     ; ECX (msg_len)
    mov ecx, [esp + 12]     ; EDX (privkey)
    mov edx, [esp + 8]      ; ESI (sig output)
    push edx
    push ecx
    push ebx
    push eax
    call ed25519_sign
    add esp, 16
    jmp .syscall_done

.syscall_ed25519_verify:
    ; ed25519_verify(msg, msg_len, pubkey, sig) -> 0 if valid, -1 if invalid
    ; EBX = message pointer
    ; ECX = message length
    ; EDX = 32-byte public key
    ; ESI = 64-byte signature
    extern ed25519_verify
    mov eax, [esp + 20]     ; EBX (msg)
    mov ebx, [esp + 16]     ; ECX (msg_len)
    mov ecx, [esp + 12]     ; EDX (pubkey)
    mov edx, [esp + 8]      ; ESI (sig)
    push edx
    push ecx
    push ebx
    push eax
    call ed25519_verify
    add esp, 16
    jmp .syscall_done

; ============================================================================
; Unix Domain Socket Syscall Handlers (210-216)
; ============================================================================

.syscall_unix_listen:
    ; unix_listen(path) -> socket_id or -1
    ; EBX = path pointer
    extern unix_listen
    mov eax, [esp + 20]     ; EBX (path)
    push eax
    call unix_listen
    add esp, 4
    jmp .syscall_done

.syscall_unix_connect:
    ; unix_connect(path) -> socket_id or -1
    ; EBX = path pointer
    extern unix_connect
    mov eax, [esp + 20]     ; EBX (path)
    push eax
    call unix_connect
    add esp, 4
    jmp .syscall_done

.syscall_unix_accept:
    ; unix_accept(listen_id) -> socket_id or -1
    ; EBX = listening socket ID
    extern unix_accept
    mov eax, [esp + 20]     ; EBX (listen_id)
    push eax
    call unix_accept
    add esp, 4
    jmp .syscall_done

.syscall_unix_send:
    ; unix_send(socket_id, data, length) -> bytes sent or -1
    ; EBX = socket_id, ECX = data pointer, EDX = length
    extern unix_send
    mov eax, [esp + 12]     ; EDX (length)
    push eax
    mov eax, [esp + 20]     ; ECX (data)
    push eax
    mov eax, [esp + 28]     ; EBX (socket_id)
    push eax
    call unix_send
    add esp, 12
    jmp .syscall_done

.syscall_unix_recv:
    ; unix_recv(socket_id, buf, max_len) -> bytes received or -1
    ; EBX = socket_id, ECX = buf pointer, EDX = max_len
    extern unix_recv
    mov eax, [esp + 12]     ; EDX (max_len)
    push eax
    mov eax, [esp + 20]     ; ECX (buf)
    push eax
    mov eax, [esp + 28]     ; EBX (socket_id)
    push eax
    call unix_recv
    add esp, 12
    jmp .syscall_done

.syscall_unix_close:
    ; unix_close(socket_id)
    ; EBX = socket_id
    extern unix_close
    mov eax, [esp + 20]     ; EBX (socket_id)
    push eax
    call unix_close
    add esp, 4
    xor eax, eax            ; Return 0 for success
    jmp .syscall_done

.syscall_unix_has_data:
    ; unix_has_data(socket_id) -> 1 if data, 0 if not
    ; EBX = socket_id
    extern unix_has_data
    mov eax, [esp + 20]     ; EBX (socket_id)
    push eax
    call unix_has_data
    add esp, 4
    jmp .syscall_done

.syscall_done:
    ; Store return value where EAX will be restored from
    mov [esp + 8], eax

    ; Restore segments
    pop es
    pop ds

    ; Restore registers (EAX now has return value)
    pop eax
    pop ebx
    pop ecx
    pop edx
    pop esi
    pop edi
    pop ebp

    ; Return from interrupt
    sti
    iret

; ============================================================================
; Linux Syscall Handler (int 0x80)
; Handles basic Linux-compatible syscalls for userland programs
; EAX = syscall number, EBX/ECX/EDX/ESI/EDI = arguments
; ============================================================================
global isr_linux_syscall
isr_linux_syscall:
    ; Save all registers
    push ebp
    push edi
    push esi
    push edx
    push ecx
    push ebx
    push eax

    ; Save segment registers
    push ds
    push es

    ; Load kernel data segment
    mov bx, 0x10
    mov ds, bx
    mov es, bx

    ; EAX = syscall number (already on stack)
    ; Get syscall number from stack
    mov eax, [esp + 8]      ; EAX from stack

    ; Handle specific syscalls
    cmp eax, 1              ; SYS_exit
    je .linux_exit

    cmp eax, 4              ; SYS_write
    je .linux_write

    ; Unknown syscall - return -1
    mov eax, -1
    jmp .linux_done

.linux_exit:
    ; exit() - for now just return to caller
    ; In a real OS we'd terminate the process
    xor eax, eax
    jmp .linux_done

.linux_write:
    ; write(fd, buf, count)
    ; EBX = fd, ECX = buf, EDX = count
    mov ebx, [esp + 12]     ; EBX (fd)
    mov ecx, [esp + 16]     ; ECX (buf)
    mov edx, [esp + 20]     ; EDX (count)

    ; For now, only handle fd 1 (stdout) - write to serial
    cmp ebx, 1
    jne .linux_write_stderr
    jmp .linux_do_write

.linux_write_stderr:
    cmp ebx, 2              ; stderr
    jne .linux_write_fail

.linux_do_write:
    ; Write to serial port (COM1 = 0x3F8)
    mov esi, ecx            ; Source buffer
    mov ecx, edx            ; Count
    xor edx, edx            ; Bytes written

.linux_write_loop:
    cmp edx, ecx
    jge .linux_write_done

    ; Wait for transmit buffer empty
    push dx
    mov dx, 0x3FD           ; Line status register
.linux_wait_tx:
    in al, dx
    test al, 0x20           ; Check if transmit buffer empty
    jz .linux_wait_tx
    pop dx

    ; Send character
    push dx
    mov al, [esi + edx]
    mov dx, 0x3F8
    out dx, al
    pop dx

    inc edx
    jmp .linux_write_loop

.linux_write_done:
    mov eax, edx            ; Return bytes written
    jmp .linux_done

.linux_write_fail:
    mov eax, -1

.linux_done:
    ; Store return value
    mov [esp + 8], eax

    ; Restore segments
    pop es
    pop ds

    ; Restore registers
    pop eax                 ; Now has return value
    pop ebx
    pop ecx
    pop edx
    pop esi
    pop edi
    pop ebp

    sti
    iret
