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
map_page:
    ; TODO: Implement page mapping
    xor eax, eax
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
; Process/Scheduler Stubs
; ============================================================================

global init_scheduler
init_scheduler:
    ret

global create_process
create_process:
    mov eax, 1  ; Return PID 1
    ret

global schedule
schedule:
    xor eax, eax
    ret

global context_switch
context_switch:
    ret

global yield
yield:
    hlt
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
    mov rax, [rel current_pid]
    ret

global set_process_state
set_process_state:
    ret

global thread_create
thread_create:
    xor eax, eax
    ret

global thread_exit
thread_exit:
    ret

global thread_yield
thread_yield:
    ; Just return - no threading support yet
    ret

global get_thread_id
get_thread_id:
    xor eax, eax
    ret

global is_thread
is_thread:
    xor eax, eax
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
; ChaCha20 Encryption
; ============================================================================

global chacha20_encrypt
chacha20_encrypt:
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
; Port I/O Functions (alternative names)
; ============================================================================

global port_inb
port_inb:
    mov dx, di
    in al, dx
    movzx eax, al
    ret

global port_outb
port_outb:
    mov dx, di
    mov al, sil
    out dx, al
    ret

global port_inw
port_inw:
    mov dx, di
    in ax, dx
    movzx eax, ax
    ret

global port_outw
port_outw:
    mov dx, di
    mov ax, si
    out dx, ax
    ret

global port_inl
port_inl:
    mov dx, di
    in eax, dx
    ret

global port_outl
port_outl:
    mov dx, di
    mov eax, esi
    out dx, eax
    ret

; ============================================================================
; MMIO Functions
; ============================================================================

global mmio_read32
mmio_read32:
    mov eax, [rdi]
    ret

global mmio_write32
mmio_write32:
    mov [rdi], esi
    ret

; ============================================================================
; PCI Functions
; ============================================================================

global pci_config_read8
pci_config_read8:
    ; RDI = bus, RSI = device, RDX = function, RCX = offset
    push rbx
    ; Build config address
    mov eax, 0x80000000
    shl edi, 16
    or eax, edi
    shl esi, 11
    or eax, esi
    shl edx, 8
    or eax, edx
    and ecx, 0xFC
    or eax, ecx
    ; Write address
    mov dx, 0xCF8
    out dx, eax
    ; Read data
    mov dx, 0xCFC
    in eax, dx
    pop rbx
    ; Return byte based on offset
    movzx eax, al
    ret

global pci_config_read16
pci_config_read16:
    push rbx
    mov eax, 0x80000000
    shl edi, 16
    or eax, edi
    shl esi, 11
    or eax, esi
    shl edx, 8
    or eax, edx
    and ecx, 0xFC
    or eax, ecx
    mov dx, 0xCF8
    out dx, eax
    mov dx, 0xCFC
    in eax, dx
    pop rbx
    movzx eax, ax
    ret

global pci_config_read32
pci_config_read32:
    push rbx
    mov eax, 0x80000000
    shl edi, 16
    or eax, edi
    shl esi, 11
    or eax, esi
    shl edx, 8
    or eax, edx
    and ecx, 0xFC
    or eax, ecx
    mov dx, 0xCF8
    out dx, eax
    mov dx, 0xCFC
    in eax, dx
    pop rbx
    ret

global pci_config_write32
pci_config_write32:
    ; RDI = bus, RSI = device, RDX = function, RCX = offset, R8 = value
    push rbx
    mov eax, 0x80000000
    shl edi, 16
    or eax, edi
    shl esi, 11
    or eax, esi
    shl edx, 8
    or eax, edx
    and ecx, 0xFC
    or eax, ecx
    mov dx, 0xCF8
    out dx, eax
    mov dx, 0xCFC
    mov eax, r8d
    out dx, eax
    pop rbx
    ret

; ============================================================================
; Memory Copy Function
; ============================================================================

global net_memcpy
net_memcpy:
    ; RDI = dest, RSI = src, RDX = count
    push rcx
    mov rcx, rdx
    rep movsb
    pop rcx
    ret

; ============================================================================
; Timer Wait Functions
; ============================================================================

global wait_tick
wait_tick:
    hlt
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
