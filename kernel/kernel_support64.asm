; kernel_support64.asm - 64-bit Kernel Support Functions
; Provides all extern functions required by the kernel

[BITS 64]

section .data

; Serial port addresses
SERIAL_PORT equ 0x3F8

; VGA constants
VGA_MEMORY equ 0xB8000
VGA_WIDTH equ 80
VGA_HEIGHT equ 25

; Cursor position
vga_cursor_x: dq 0
vga_cursor_y: dq 0

; Tick counter (incremented by timer)
global tick_count
tick_count: dq 0

; Current process ID
current_pid: dq 1

; Keyboard buffer
kbd_buffer: times 256 db 0
kbd_head: dq 0
kbd_tail: dq 0

; Page table allocation tracking
; Use 0x6000-0x1FFFF for dynamic page tables (about 100KB = 25 page tables)
next_page_table: dq 0x6000

section .bss
; Reserved space for various subsystems
resb 4096  ; Reserved space

section .text

; ============================================================================
; Serial Port Functions
; ============================================================================

global serial_init
serial_init:
    push rbx
    ; Disable interrupts
    mov dx, SERIAL_PORT + 1
    xor al, al
    out dx, al
    ; Enable DLAB
    mov dx, SERIAL_PORT + 3
    mov al, 0x80
    out dx, al
    ; Set baud rate divisor (115200)
    mov dx, SERIAL_PORT
    mov al, 1
    out dx, al
    mov dx, SERIAL_PORT + 1
    xor al, al
    out dx, al
    ; 8 bits, no parity, one stop bit
    mov dx, SERIAL_PORT + 3
    mov al, 0x03
    out dx, al
    ; Enable FIFO
    mov dx, SERIAL_PORT + 2
    mov al, 0xC7
    out dx, al
    ; Enable IRQs
    mov dx, SERIAL_PORT + 4
    mov al, 0x0B
    out dx, al
    pop rbx
    ret

global serial_putchar
serial_putchar:
    ; RDI = character
    push rbx
    mov rbx, rdi
.wait:
    mov dx, SERIAL_PORT + 5
    in al, dx
    test al, 0x20
    jz .wait
    mov dx, SERIAL_PORT
    mov al, bl
    out dx, al
    pop rbx
    ret

global serial_print
serial_print:
    ; RDI = string pointer
    push rbx
    push r12
    mov r12, rdi
.loop:
    movzx rdi, byte [r12]
    test dil, dil
    jz .done
    call serial_putchar
    inc r12
    jmp .loop
.done:
    pop r12
    pop rbx
    ret

global serial_available
serial_available:
    mov dx, SERIAL_PORT + 5
    in al, dx
    test al, 1
    jz .no_data
    mov eax, 1
    ret
.no_data:
    xor eax, eax
    ret

global serial_getchar
serial_getchar:
    ; Non-blocking: return -1 if no data available
    mov dx, SERIAL_PORT + 5
    in al, dx
    test al, 1
    jz .no_data
    mov dx, SERIAL_PORT
    in al, dx
    movzx eax, al
    ret
.no_data:
    mov eax, -1
    ret

; Blocking version for when we really need to wait
global serial_getchar_blocking
serial_getchar_blocking:
.wait:
    mov dx, SERIAL_PORT + 5
    in al, dx
    test al, 1
    jz .wait
    mov dx, SERIAL_PORT
    in al, dx
    movzx eax, al
    ret

; ============================================================================
; VGA Functions
; ============================================================================

global vga_init
vga_init:
    ; Clear screen
    mov rdi, VGA_MEMORY
    mov rcx, VGA_WIDTH * VGA_HEIGHT
    mov ax, 0x0720  ; Space with light gray on black
    rep stosw
    ; Reset cursor
    mov qword [rel vga_cursor_x], 0
    mov qword [rel vga_cursor_y], 0
    ret

global vga_putchar
vga_putchar:
    ; RDI = character
    push rbx
    push r12
    push r13

    mov r12, rdi  ; Save character

    ; Handle newline
    cmp r12d, 10
    jne .not_newline
    mov qword [rel vga_cursor_x], 0
    inc qword [rel vga_cursor_y]
    jmp .check_scroll

.not_newline:
    ; Handle carriage return
    cmp r12d, 13
    jne .regular
    mov qword [rel vga_cursor_x], 0
    jmp .done

.regular:
    ; Calculate VGA offset
    mov rax, [rel vga_cursor_y]
    imul rax, VGA_WIDTH
    add rax, [rel vga_cursor_x]
    shl rax, 1
    add rax, VGA_MEMORY

    ; Write character with attribute
    mov byte [rax], r12b
    mov byte [rax + 1], 0x07  ; Light gray on black

    ; Advance cursor
    inc qword [rel vga_cursor_x]
    cmp qword [rel vga_cursor_x], VGA_WIDTH
    jl .check_scroll
    mov qword [rel vga_cursor_x], 0
    inc qword [rel vga_cursor_y]

.check_scroll:
    cmp qword [rel vga_cursor_y], VGA_HEIGHT
    jl .done
    ; Scroll up (TODO: implement scrolling)
    mov qword [rel vga_cursor_y], VGA_HEIGHT - 1

.done:
    pop r13
    pop r12
    pop rbx
    ret

global vga_print
vga_print:
    ; RDI = string pointer
    push r12
    mov r12, rdi
.loop:
    movzx rdi, byte [r12]
    test dil, dil
    jz .done
    push r12
    call vga_putchar
    pop r12
    inc r12
    jmp .loop
.done:
    pop r12
    ret

global vga_clear
vga_clear:
    call vga_init
    ret

global vga_setcursor
vga_setcursor:
    ; RDI = x, RSI = y
    mov [rel vga_cursor_x], rdi
    mov [rel vga_cursor_y], rsi
    ret

global vga_set_color
vga_set_color:
    ; RDI = color (ignored for now)
    ret

; ============================================================================
; Keyboard Functions
; ============================================================================

; keyboard_handler - called by IRQ1 from isr64.asm
global keyboard_handler
keyboard_handler:
    push rax
    push rbx
    push rcx

    ; Read scancode
    in al, 0x60

    ; Ignore key releases (high bit set)
    test al, 0x80
    jnz .done

    ; Very basic scancode table (just letters and numbers)
    movzx rbx, al
    lea rcx, [rel scancode_table]
    movzx rax, byte [rcx + rbx]
    test al, al
    jz .done

    ; Add to buffer
    mov rbx, [rel kbd_tail]
    lea rcx, [rel kbd_buffer]
    mov [rcx + rbx], al
    inc rbx
    and rbx, 0xFF
    mov [rel kbd_tail], rbx

.done:
    pop rcx
    pop rbx
    pop rax
    ret

global keyboard_available
keyboard_available:
    mov rax, [rel kbd_head]
    cmp rax, [rel kbd_tail]
    je .no_data
    mov eax, 1
    ret
.no_data:
    xor eax, eax
    ret

global keyboard_read_char
keyboard_read_char:
    mov rax, [rel kbd_head]
    cmp rax, [rel kbd_tail]
    je .no_data
    lea rcx, [rel kbd_buffer]
    movzx eax, byte [rcx + rax]
    inc qword [rel kbd_head]
    and qword [rel kbd_head], 0xFF
    ret
.no_data:
    xor eax, eax
    ret

; ============================================================================
; Timer Functions
; ============================================================================

; Called by IRQ0 handler
global timer_tick
timer_tick:
    inc qword [rel tick_count]
    ret

global get_tick_count
get_tick_count:
    mov rax, [rel tick_count]
    ret

global sleep_ms
sleep_ms:
    ; RDI = milliseconds
    push rbx
    mov rbx, [rel tick_count]
    add rbx, rdi  ; Simple approximation (assumes ~1000 ticks/sec)
.wait:
    hlt
    cmp [rel tick_count], rbx
    jl .wait
    pop rbx
    ret

; ============================================================================
; Interrupt Control Functions
; ============================================================================

global init_idt
init_idt:
    ; IDT is now initialized in isr64.asm via setup_idt64
    ret

global remap_pic
remap_pic:
    ; ICW1
    mov al, 0x11
    out 0x20, al
    out 0xA0, al
    ; ICW2 - Remap IRQs
    mov al, 0x20  ; Master: IRQ0-7 -> INT 0x20-0x27
    out 0x21, al
    mov al, 0x28  ; Slave: IRQ8-15 -> INT 0x28-0x2F
    out 0xA1, al
    ; ICW3
    mov al, 0x04
    out 0x21, al
    mov al, 0x02
    out 0xA1, al
    ; ICW4
    mov al, 0x01
    out 0x21, al
    out 0xA1, al
    ; Unmask all IRQs
    xor al, al
    out 0x21, al
    out 0xA1, al
    ret

global enable_interrupts
enable_interrupts:
    sti
    ret

global disable_interrupts
disable_interrupts:
    cli
    ret

; ============================================================================
; Memory Functions
; ============================================================================

global init_paging
init_paging:
    ; Already set up by bootloader
    ret

global alloc_frame
alloc_frame:
    ; TODO: Implement frame allocator
    xor eax, eax
    ret

global free_frame
free_frame:
    ret

global map_page
; map_page(virtual_addr: int32, physical_addr: int32, flags: int32): int32
; RDI = virtual address, RSI = physical address, RDX = flags
; For 64-bit, we use 4-level paging: PML4 -> PDPT -> PD -> PT
; PML4 is at 0x1000 (set up by bootloader)
map_page:
    push rbx
    push rcx
    push r8
    push r9
    push r10
    push r11

    ; Zero-extend 32-bit addresses to 64-bit
    mov rdi, rdi
    and rdi, 0xFFFFFFFF
    mov rsi, rsi
    and rsi, 0xFFFFFFFF
    mov rdx, rdx
    and rdx, 0xFF              ; Only lower bits of flags matter

    ; Calculate page table indices
    ; PML4 index = (vaddr >> 39) & 0x1FF
    mov rax, rdi
    shr rax, 39
    and rax, 0x1FF
    mov r8, rax                ; r8 = PML4 index

    ; PDPT index = (vaddr >> 30) & 0x1FF
    mov rax, rdi
    shr rax, 30
    and rax, 0x1FF
    mov r9, rax                ; r9 = PDPT index

    ; PD index = (vaddr >> 21) & 0x1FF
    mov rax, rdi
    shr rax, 21
    and rax, 0x1FF
    mov r10, rax               ; r10 = PD index

    ; PT index = (vaddr >> 12) & 0x1FF
    mov rax, rdi
    shr rax, 12
    and rax, 0x1FF
    mov r11, rax               ; r11 = PT index

    ; PML4 is at 0x1000
    mov rbx, 0x1000

    ; Get PML4 entry
    mov rax, [rbx + r8*8]
    test rax, 1                ; Check present bit
    jnz .have_pdpt

    ; Need to allocate PDPT
    mov rax, [rel next_page_table]
    mov rcx, rax
    add rcx, 4096
    mov [rel next_page_table], rcx

    ; Clear new PDPT
    push rdi
    mov rdi, rax
    push rax
    xor eax, eax
    mov rcx, 512
    rep stosq
    pop rax
    pop rdi

    ; Set PML4 entry to new PDPT
    or rax, 0x03               ; Present + Writable
    mov [rbx + r8*8], rax
    and rax, 0xFFFFFFFFFFFFF000 ; Get address only

.have_pdpt:
    ; rax = PDPT address (with flags), get address only
    and rax, 0xFFFFFFFFFFFFF000
    mov rbx, rax               ; rbx = PDPT address

    ; Get PDPT entry
    mov rax, [rbx + r9*8]
    test rax, 1                ; Check present bit
    jnz .have_pd

    ; Need to allocate PD
    mov rax, [rel next_page_table]
    mov rcx, rax
    add rcx, 4096
    mov [rel next_page_table], rcx

    ; Clear new PD
    push rdi
    mov rdi, rax
    push rax
    xor eax, eax
    mov rcx, 512
    rep stosq
    pop rax
    pop rdi

    ; Set PDPT entry to new PD
    or rax, 0x03               ; Present + Writable
    mov [rbx + r9*8], rax
    and rax, 0xFFFFFFFFFFFFF000

.have_pd:
    and rax, 0xFFFFFFFFFFFFF000
    mov rbx, rax               ; rbx = PD address

    ; Get PD entry
    mov rax, [rbx + r10*8]
    test rax, 1                ; Check present bit
    jnz .have_pt

    ; Need to allocate PT
    mov rax, [rel next_page_table]
    mov rcx, rax
    add rcx, 4096
    mov [rel next_page_table], rcx

    ; Clear new PT
    push rdi
    mov rdi, rax
    push rax
    xor eax, eax
    mov rcx, 512
    rep stosq
    pop rax
    pop rdi

    ; Set PD entry to new PT
    or rax, 0x03               ; Present + Writable
    mov [rbx + r10*8], rax
    and rax, 0xFFFFFFFFFFFFF000

.have_pt:
    and rax, 0xFFFFFFFFFFFFF000
    mov rbx, rax               ; rbx = PT address

    ; Set PT entry to physical page
    mov rax, rsi               ; Physical address
    and rax, 0xFFFFFFFFFFFFF000 ; Page-align
    or rax, rdx                ; Add flags
    or rax, 1                  ; Ensure present bit is set
    mov [rbx + r11*8], rax

    ; Invalidate TLB entry for this virtual address
    invlpg [rdi]

    mov eax, 1                 ; Success

    pop r11
    pop r10
    pop r9
    pop r8
    pop rcx
    pop rbx
    ret

global get_physical_address
get_physical_address:
    mov rax, rdi
    ret

global flush_tlb
flush_tlb:
    mov rax, cr3
    mov cr3, rax
    ret

global set_cr3
set_cr3:
    mov cr3, rdi
    ret

global get_cr3
get_cr3:
    mov rax, cr3
    ret

; ============================================================================
; Threading System - Cooperative Multithreading
; ============================================================================

; Thread states
THREAD_FREE     equ 0
THREAD_READY    equ 1
THREAD_RUNNING  equ 2
THREAD_BLOCKED  equ 3
THREAD_DEAD     equ 4

; Thread Control Block (TCB) - 64 bytes each
; Offset 0:  rsp (saved stack pointer)
; Offset 8:  state
; Offset 16: tid
; Offset 24: entry
; Offset 32: arg
; Offset 40: stack_base
; Offset 48-63: reserved

MAX_THREADS     equ 16
THREAD_STACK_SIZE equ 8192  ; 8KB per thread stack
TCB_SIZE        equ 64

section .bss
align 16
thread_table:   resb MAX_THREADS * TCB_SIZE
thread_stacks:  resb MAX_THREADS * THREAD_STACK_SIZE
current_thread: resq 1      ; Index of currently running thread
thread_count:   resq 1      ; Number of active threads
scheduler_lock: resq 1      ; Simple spinlock

section .text

global init_scheduler
init_scheduler:
    push rbx
    push rcx

    ; Clear thread table
    lea rdi, [thread_table]
    mov rcx, MAX_THREADS * TCB_SIZE / 8
    xor rax, rax
    rep stosq

    ; Initialize main thread (thread 0)
    lea rdi, [thread_table]
    mov qword [rdi + 8], THREAD_RUNNING  ; state = RUNNING
    mov qword [rdi + 16], 0              ; tid = 0

    mov qword [current_thread], 0
    mov qword [thread_count], 1
    mov qword [scheduler_lock], 0

    pop rcx
    pop rbx
    ret

global create_process
create_process:
    mov eax, 1  ; Return PID 1
    ret

global schedule
schedule:
    ; Find next ready thread (round-robin)
    push rbx
    push rcx
    push rdx

    mov rax, [current_thread]
    mov rcx, MAX_THREADS

.find_next:
    inc rax
    cmp rax, MAX_THREADS
    jl .check_thread
    xor rax, rax                    ; Wrap around

.check_thread:
    ; Calculate TCB address: thread_table + rax * TCB_SIZE
    mov rdx, rax
    shl rdx, 6                      ; * 64 (TCB_SIZE)
    lea rbx, [thread_table]
    add rbx, rdx

    ; Check if thread is READY
    cmp qword [rbx + 8], THREAD_READY
    je .found

    dec rcx
    jnz .find_next

    ; No ready thread found, return current
    mov rax, [current_thread]

.found:
    pop rdx
    pop rcx
    pop rbx
    ret

global context_switch
context_switch:
    ; RDI = new thread index
    ; Note: called from thread_exit, no need to save current state
    ; (current thread is already marked DEAD)

    ; Switch to new thread
    mov [current_thread], rdi

    ; Calculate new TCB address
    mov rax, rdi
    shl rax, 6
    lea rcx, [thread_table]
    add rcx, rax

    ; Mark as RUNNING
    mov qword [rcx + 8], THREAD_RUNNING

    ; Restore new thread's RSP
    mov rsp, [rcx]

    ; The new thread's stack was saved by thread_yield with:
    ; push rbx, push r12, push r13, push r14, push r15, push rbp
    ; So we need to pop them all in reverse order
    pop rbp
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

global yield
yield:
    call thread_yield
    ret

global exit_process
exit_process:
    jmp $  ; Hang

global fork
fork:
    xor eax, eax  ; Return 0 (child)
    ret

global get_current_pid
get_current_pid:
    mov rax, [current_thread]
    ret

global set_process_state
set_process_state:
    ret

global thread_create
thread_create:
    ; RDI = entry point, RSI = arg
    ; Returns thread ID or -1 on error
    push rbx
    push r12
    push r13
    push r14

    mov r12, rdi        ; Save entry
    mov r13, rsi        ; Save arg

    ; Find free thread slot
    xor rcx, rcx        ; Start at 1 (0 is main thread)
    inc rcx

.find_slot:
    cmp rcx, MAX_THREADS
    jge .no_slot

    mov rax, rcx
    shl rax, 6
    lea rbx, [thread_table]
    add rbx, rax

    cmp qword [rbx + 8], THREAD_FREE
    je .found_slot
    cmp qword [rbx + 8], THREAD_DEAD
    je .found_slot

    inc rcx
    jmp .find_slot

.no_slot:
    mov rax, -1
    jmp .done

.found_slot:
    ; RCX = thread index, RBX = TCB pointer
    mov r14, rcx        ; Save thread index

    ; Calculate stack address: thread_stacks + rcx * THREAD_STACK_SIZE + THREAD_STACK_SIZE
    mov rax, rcx
    shl rax, 13         ; * 8192 (THREAD_STACK_SIZE)
    lea rdx, [thread_stacks]
    add rdx, rax
    add rdx, THREAD_STACK_SIZE  ; Top of stack

    ; Set up initial stack frame for new thread
    ; Stack layout matches what thread_yield expects when it pops:
    ; pop rbp, pop r15, pop r14, pop r13, pop r12, pop rbx, ret
    ; So from RSP upward: rbp, r15, r14, r13, r12, rbx, return_addr

    ; Start from top of stack
    ; First, push the return address for when thread_start returns
    sub rdx, 8
    lea rax, [thread_exit_wrapper]
    mov [rdx], rax              ; Return to exit wrapper when thread returns

    ; Now set up the stack frame that thread_yield expects
    ; thread_yield pops: rbp, r15, r14, r13, r12, rbx, then ret
    ; So we push in reverse order: ret, rbx, r12, r13, r14, r15, rbp

    sub rdx, 8
    lea rax, [thread_start]
    mov [rdx], rax              ; Return address -> thread_start

    sub rdx, 8
    mov qword [rdx], 0          ; rbx

    sub rdx, 8
    mov [rdx], r12              ; r12 = entry point

    sub rdx, 8
    mov [rdx], r13              ; r13 = arg

    sub rdx, 8
    mov qword [rdx], 0          ; r14

    sub rdx, 8
    mov qword [rdx], 0          ; r15

    sub rdx, 8
    mov qword [rdx], 0          ; rbp

    ; Fill in TCB
    mov [rbx], rdx              ; rsp
    mov qword [rbx + 8], THREAD_READY  ; state
    mov [rbx + 16], r14         ; tid
    mov [rbx + 24], r12         ; entry
    mov [rbx + 32], r13         ; arg

    ; Calculate and save stack base
    mov rax, r14
    shl rax, 13
    lea rdx, [thread_stacks]
    add rdx, rax
    mov [rbx + 40], rdx         ; stack_base

    ; Increment thread count
    inc qword [thread_count]

    mov rax, r14                ; Return thread ID

.done:
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

; Internal: start a new thread
thread_start:
    ; After context switch, callee-saved registers are restored from stack:
    ; r12 = entry point (function pointer)
    ; r13 = arg
    ; Call the entry function with arg in RDI
    mov rax, r12        ; Entry point
    mov rdi, r13        ; Arg as first parameter
    call rax
    ; If function returns, exit thread
    xor edi, edi
    call thread_exit
    jmp $               ; Should never reach here

; Internal: wrapper for thread exit
thread_exit_wrapper:
    xor edi, edi
    call thread_exit
    jmp $

global thread_exit
thread_exit:
    ; Mark current thread as DEAD
    mov rax, [current_thread]
    shl rax, 6
    lea rcx, [thread_table]
    add rcx, rax
    mov qword [rcx + 8], THREAD_DEAD

    dec qword [thread_count]

    ; Yield to another thread
    call schedule
    mov rdi, rax
    call context_switch

    ; Should never return here
    jmp $

global thread_yield
thread_yield:
    ; Save callee-saved registers
    push rbx
    push r12
    push r13
    push r14
    push r15
    push rbp

    ; Find next thread
    call schedule

    ; If same thread, just return
    cmp rax, [current_thread]
    je .same_thread

    ; Switch to new thread
    mov rdi, rax

    ; Save current RSP
    mov rax, [current_thread]
    shl rax, 6
    lea rcx, [thread_table]
    add rcx, rax
    mov [rcx], rsp

    ; Mark current as READY
    mov qword [rcx + 8], THREAD_READY

    ; Switch current_thread
    mov [current_thread], rdi

    ; Calculate new TCB
    mov rax, rdi
    shl rax, 6
    lea rcx, [thread_table]
    add rcx, rax

    ; Mark as RUNNING
    mov qword [rcx + 8], THREAD_RUNNING

    ; Restore new thread's RSP
    mov rsp, [rcx]

.same_thread:
    pop rbp
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

global get_thread_id
get_thread_id:
    mov rax, [current_thread]
    ret

global is_thread
is_thread:
    mov rax, [current_thread]
    ; Return 1 if not main thread (tid > 0)
    cmp rax, 0
    setne al
    movzx eax, al
    ret

global thread_join
thread_join:
    xor eax, eax
    ret

global thread_detach
thread_detach:
    xor eax, eax
    ret

global sys_exec
sys_exec:
    xor eax, eax
    ret

global sys_execve
sys_execve:
    xor eax, eax
    ret

global waitpid
waitpid:
    xor eax, eax
    ret

global getppid
getppid:
    xor eax, eax
    ret

; ============================================================================
; User/Group Functions
; ============================================================================

global sys_getuid
sys_getuid:
    xor eax, eax
    ret

global sys_getgid
sys_getgid:
    xor eax, eax
    ret

global sys_geteuid
sys_geteuid:
    xor eax, eax
    ret

global sys_getegid
sys_getegid:
    xor eax, eax
    ret

global sys_setuid
sys_setuid:
    xor eax, eax
    ret

global sys_setgid
sys_setgid:
    xor eax, eax
    ret

; ============================================================================
; Pipe/FD Functions
; ============================================================================

global init_pipes
init_pipes:
    ret

global setup_std_fds
setup_std_fds:
    ret

global sys_pipe
sys_pipe:
    mov eax, -1
    ret

global sys_read
sys_read:
    xor eax, eax
    ret

global sys_write
sys_write:
    ; Minimal write to serial
    mov rax, rdx  ; Return count
    ret

global sys_close
sys_close:
    xor eax, eax
    ret

global sys_dup
sys_dup:
    xor eax, eax
    ret

global sys_dup2
sys_dup2:
    xor eax, eax
    ret

; ============================================================================
; VFS Functions
; ============================================================================

global vfs_init
vfs_init:
    ret

global vfs_mount
vfs_mount:
    xor eax, eax
    ret

global vfs_mount_count
vfs_mount_count:
    xor eax, eax
    ret

global vfs_get_mount_path
vfs_get_mount_path:
    xor eax, eax
    ret

global vfs_get_mount_type
vfs_get_mount_type:
    xor eax, eax
    ret

; ============================================================================
; Signal Functions
; ============================================================================

global init_signals
init_signals:
    ret

global sys_kill
sys_kill:
    xor eax, eax
    ret

global sys_signal
sys_signal:
    xor eax, eax
    ret

global sys_raise
sys_raise:
    xor eax, eax
    ret

global check_signals
check_signals:
    xor eax, eax
    ret

; ============================================================================
; ELF Functions
; ============================================================================

global elf_validate
elf_validate:
    xor eax, eax
    ret

global elf_load
elf_load:
    xor eax, eax
    ret

global call_entry_with_stack
call_entry_with_stack:
    ; TODO: Implement ELF entry call
    ret

; ============================================================================
; Syscall Functions
; ============================================================================

global syscall1
syscall1:
    xor eax, eax
    ret

global syscall2
syscall2:
    xor eax, eax
    ret

; ============================================================================
; ATA/Disk Stubs
; ============================================================================

global ata_irq14_handler
ata_irq14_handler:
    ret

global ata_irq15_handler
ata_irq15_handler:
    ret

global ata_init
ata_init:
    ret

global ata_read_sector
ata_read_sector:
    xor eax, eax
    ret

global ata_write_sector
ata_write_sector:
    xor eax, eax
    ret

global ata_identify
ata_identify:
    mov eax, 1          ; Return 1 = drive not found (stub)
    ret

global ata_get_identify_buffer
ata_get_identify_buffer:
    xor eax, eax
    ret

global ata_soft_reset
ata_soft_reset:
    ret

global ata_read_sectors_pio
ata_read_sectors_pio:
    xor eax, eax
    ret

global ata_write_sectors_pio
ata_write_sectors_pio:
    xor eax, eax
    ret

; ============================================================================
; Networking Stubs
; ============================================================================

global net_init
net_init:
    ret

global net_send_packet
net_send_packet:
    ret

global rtl8139_irq_handler
rtl8139_irq_handler:
    ret

; ============================================================================
; Port I/O Functions
; ============================================================================

global inb
inb:
    mov dx, di
    in al, dx
    movzx eax, al
    ret

global outb
outb:
    mov dx, di
    mov al, sil
    out dx, al
    ret

global inw
inw:
    mov dx, di
    in ax, dx
    movzx eax, ax
    ret

global outw
outw:
    mov dx, di
    mov ax, si
    out dx, ax
    ret

global inl
inl:
    mov dx, di
    in eax, dx
    ret

global outl
outl:
    mov dx, di
    mov eax, esi
    out dx, eax
    ret

; ============================================================================
; Multiboot Framebuffer Info
; ============================================================================

; Multiboot framebuffer data storage
multiboot_fb_addr_data: dq 0xB8000
multiboot_fb_width_data: dd 80
multiboot_fb_height_data: dd 25
multiboot_fb_bpp_data: dd 16
multiboot_fb_pitch_data: dd 160

; Multiboot framebuffer getter functions
global multiboot_fb_addr
multiboot_fb_addr:
    mov eax, [rel multiboot_fb_addr_data]
    ret

global multiboot_fb_width
multiboot_fb_width:
    mov eax, [rel multiboot_fb_width_data]
    ret

global multiboot_fb_height
multiboot_fb_height:
    mov eax, [rel multiboot_fb_height_data]
    ret

global multiboot_fb_bpp
multiboot_fb_bpp:
    mov eax, [rel multiboot_fb_bpp_data]
    ret

global multiboot_fb_pitch
multiboot_fb_pitch:
    mov eax, [rel multiboot_fb_pitch_data]
    ret

; ============================================================================
; VTNext Functions
; ============================================================================

global vtn_set_fb_info
vtn_set_fb_info:
    ret

global vtn_init
vtn_init:
    ret

global vtn_get_fb_addr
vtn_get_fb_addr:
    mov rax, [rel multiboot_fb_addr_data]
    ret

global vtn_get_fb_width
vtn_get_fb_width:
    mov eax, [rel multiboot_fb_width_data]
    ret

global vtn_get_fb_height
vtn_get_fb_height:
    mov eax, [rel multiboot_fb_height_data]
    ret

global vtn_set_input_mode
vtn_set_input_mode:
    ret

global vtn_set_cursor_visible
vtn_set_cursor_visible:
    ret

global vtn_set_viewport
vtn_set_viewport:
    ret

global vtn_get_modifiers
vtn_get_modifiers:
    xor eax, eax
    ret

global vtn_get_timestamp
vtn_get_timestamp:
    mov rax, [rel tick_count]
    ret

; ============================================================================
; Device Filesystem Functions
; ============================================================================

global devfs_init
devfs_init:
    ret

global tty_init
tty_init:
    ret

global keyboard_init
keyboard_init:
    ret

global devfs_get_device_count
devfs_get_device_count:
    xor eax, eax
    ret

global devfs_get_name
devfs_get_name:
    xor eax, eax
    ret

global devfs_get_type
devfs_get_type:
    xor eax, eax
    ret

; ============================================================================
; Process State Functions
; ============================================================================

global get_process_state
get_process_state:
    xor eax, eax
    ret

; ============================================================================
; Embedded Binary Getters (stubs - return null/0)
; ============================================================================

global get_vtn_pong_bin
get_vtn_pong_bin:
    xor eax, eax
    ret

global get_vtn_pong_bin_size
get_vtn_pong_bin_size:
    xor eax, eax
    ret

global get_vtn_edit_bin
get_vtn_edit_bin:
    xor eax, eax
    ret

global get_vtn_edit_bin_size
get_vtn_edit_bin_size:
    xor eax, eax
    ret

global get_vtn_shell_bin
get_vtn_shell_bin:
    xor eax, eax
    ret

global get_vtn_shell_bin_size
get_vtn_shell_bin_size:
    xor eax, eax
    ret

global get_2048_bin
get_2048_bin:
    xor eax, eax
    ret

global get_2048_bin_size
get_2048_bin_size:
    xor eax, eax
    ret

global get_webapp_bin
get_webapp_bin:
    xor eax, eax
    ret

global get_webapp_bin_size
get_webapp_bin_size:
    xor eax, eax
    ret

; ============================================================================
; Entry Point Callers
; ============================================================================

global call_entry
call_entry:
    ; RDI = entry point
    call rdi
    ret

; ============================================================================
; Scancode to ASCII table
; ============================================================================

section .rodata
scancode_table:
    db 0, 27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 8, 9
    db 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', 13, 0, 'a', 's'
    db 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", '`', 0, '\', 'z', 'x', 'c', 'v'
    db 'b', 'n', 'm', ',', '.', '/', 0, '*', 0, ' ', 0, 0, 0, 0, 0, 0
    times 192 db 0
