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

    cmp eax, 5          ; SYS_getpid
    je .syscall_getpid

    cmp eax, 6          ; SYS_yield
    je .syscall_yield

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

    ; Unknown syscall - return -1
    mov eax, -1
    jmp .syscall_done

.syscall_exit:
    ; exit() - for now just halt
    cli
    hlt
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
    ; wait() - yield until child exits
    ; For now, just yield
    call yield
    xor eax, eax
    jmp .syscall_done

; ============= Networking syscalls =============

.syscall_net_listen:
    ; net_listen(port) -> conn
    ; EBX = port
    extern tcp_listen
    mov eax, [esp + 20]     ; EBX (port)
    push eax
    call tcp_listen
    add esp, 4
    jmp .syscall_done

.syscall_net_accept:
    ; net_accept_ready(conn) -> 0/1
    ; EBX = conn
    extern tcp_accept_ready
    mov eax, [esp + 20]     ; EBX (conn)
    push eax
    call tcp_accept_ready
    add esp, 4
    jmp .syscall_done

.syscall_net_connect:
    ; net_connect(ip_ptr, port) -> conn
    ; EBX = ip_ptr, ECX = port
    extern tcp_connect
    mov eax, [esp + 20]     ; EBX (ip_ptr)
    mov ebx, [esp + 16]     ; ECX (port)
    push ebx                ; port
    push eax                ; ip_ptr
    call tcp_connect
    add esp, 8
    jmp .syscall_done

.syscall_net_send:
    ; net_send(conn, data, len) -> sent
    ; EBX = conn, ECX = data, EDX = len
    extern tcp_write
    mov eax, [esp + 20]     ; EBX (conn)
    mov ebx, [esp + 16]     ; ECX (data)
    mov ecx, [esp + 12]     ; EDX (len)
    push ecx                ; len
    push ebx                ; data
    push eax                ; conn
    call tcp_write
    add esp, 12
    jmp .syscall_done

.syscall_net_recv:
    ; net_recv(conn, buf, max_len) -> read
    ; EBX = conn, ECX = buf, EDX = max_len
    extern tcp_read
    mov eax, [esp + 20]     ; EBX (conn)
    mov ebx, [esp + 16]     ; ECX (buf)
    mov ecx, [esp + 12]     ; EDX (max_len)
    push ecx                ; max_len
    push ebx                ; buf
    push eax                ; conn
    call tcp_read
    add esp, 12
    jmp .syscall_done

.syscall_net_close:
    ; net_close(conn)
    ; EBX = conn
    extern tcp_close
    mov eax, [esp + 20]     ; EBX (conn)
    push eax
    call tcp_close
    add esp, 4
    xor eax, eax            ; return 0
    jmp .syscall_done

.syscall_net_state:
    ; net_state(conn) -> state
    ; EBX = conn
    ; Returns tcp_state[conn]
    extern tcp_state
    mov eax, [esp + 20]     ; EBX (conn)
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
