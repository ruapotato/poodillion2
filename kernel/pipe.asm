; pipe.asm - Pipe and file descriptor management for BrainhairOS
; Implements Unix-style pipes and file descriptor table

bits 32

; File descriptor types
FD_UNUSED       equ 0
FD_PIPE_READ    equ 1
FD_PIPE_WRITE   equ 2
FD_FILE         equ 3
FD_TTY          equ 4
FD_DEV_NULL     equ 5

; File descriptor entry (8 bytes)
; Offset 0: type (int32)
; Offset 4: data (int32 - pipe index, file inode, etc.)
FD_ENTRY_SIZE   equ 8

; Maximum FDs per process
MAX_FDS         equ 16

; Maximum number of pipes (reduced from 32 to 8 to save BSS space)
MAX_PIPES       equ 8

; Pipe buffer size (1KB)
PIPE_BUF_SIZE   equ 1024

; Pipe structure (1032 bytes)
; Offset 0: flags (int32) - 0=free, 1=active
; Offset 4: read_pos (int32)
; Offset 8: write_pos (int32)
; Offset 12: count (int32) - bytes in buffer
; Offset 16: read_pid (int32) - process holding read end
; Offset 20: write_pid (int32) - process holding write end
; Offset 24: buffer[1024]
PIPE_FLAGS      equ 0
PIPE_READ_POS   equ 4
PIPE_WRITE_POS  equ 8
PIPE_COUNT      equ 12
PIPE_READ_PID   equ 16
PIPE_WRITE_PID  equ 20
PIPE_BUFFER     equ 24
PIPE_STRUCT_SIZE equ 1048

section .data

msg_pipe_create: db "[PIPE] Created pipe ", 0
msg_pipe_full:   db "[PIPE] Buffer full", 0

section .bss

; File descriptor table (per-process, 16 FDs * 8 bytes * 16 processes = 2KB)
align 4
global fd_table
fd_table:
    resb FD_ENTRY_SIZE * MAX_FDS * 16  ; 16 processes

; Pipe buffers
align 4
global pipe_table
pipe_table:
    resb PIPE_STRUCT_SIZE * MAX_PIPES

section .text

; ============================================================================
; init_pipes - Initialize pipe subsystem
; ============================================================================
global init_pipes

init_pipes:
    push ecx
    push edi

    ; Clear fd_table (2KB)
    mov edi, fd_table
    mov ecx, (FD_ENTRY_SIZE * MAX_FDS * 16) / 4
    xor eax, eax
    rep stosd

    ; Clear pipe_table
    mov edi, pipe_table
    mov ecx, (PIPE_STRUCT_SIZE * MAX_PIPES) / 4
    xor eax, eax
    rep stosd

    pop edi
    pop ecx
    xor eax, eax            ; Return 0 (success)
    ret

; ============================================================================
; get_fd_entry - Get pointer to FD entry for a process
; Input: EAX = pid, EBX = fd number
; Returns: EAX = pointer to FD entry, or 0 if invalid
; ============================================================================
global get_fd_entry
get_fd_entry:
    ; Validate inputs
    cmp eax, 16
    jge .invalid
    cmp ebx, MAX_FDS
    jge .invalid

    ; Calculate offset: fd_table + (pid * MAX_FDS + fd) * FD_ENTRY_SIZE
    push edx
    mov edx, MAX_FDS
    imul eax, edx           ; pid * MAX_FDS
    add eax, ebx            ; + fd
    imul eax, FD_ENTRY_SIZE ; * entry size
    add eax, fd_table
    pop edx
    ret

.invalid:
    xor eax, eax
    ret

; ============================================================================
; fd_alloc - Allocate a free FD for current process
; Returns: EAX = FD number (0-15), or -1 if none free
; ============================================================================
global fd_alloc
fd_alloc:
    push ebx
    push ecx
    push edx

    ; Get current PID
    extern current_pid
    mov eax, [current_pid]

    ; Search for free FD
    mov ecx, 0              ; FD counter

.search:
    cmp ecx, MAX_FDS
    jge .none_free

    mov ebx, ecx
    push eax
    push ecx
    call get_fd_entry
    pop ecx
    mov edx, eax            ; EDX = FD entry pointer
    pop eax

    ; Check if unused
    cmp dword [edx], FD_UNUSED
    je .found

    inc ecx
    jmp .search

.found:
    mov eax, ecx
    pop edx
    pop ecx
    pop ebx
    ret

.none_free:
    mov eax, -1
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; pipe_create - Create a new pipe
; Returns: EAX = pipe index, or -1 if none free
; ============================================================================
global pipe_create
pipe_create:
    push ebx
    push ecx
    push edi

    ; Search for free pipe slot
    mov ecx, 0
    mov edi, pipe_table

.search:
    cmp ecx, MAX_PIPES
    jge .none_free

    cmp dword [edi + PIPE_FLAGS], 0
    je .found

    add edi, PIPE_STRUCT_SIZE
    inc ecx
    jmp .search

.found:
    ; Initialize pipe
    mov dword [edi + PIPE_FLAGS], 1     ; Active
    mov dword [edi + PIPE_READ_POS], 0
    mov dword [edi + PIPE_WRITE_POS], 0
    mov dword [edi + PIPE_COUNT], 0
    mov dword [edi + PIPE_READ_PID], -1
    mov dword [edi + PIPE_WRITE_PID], -1

    ; Return pipe index
    mov eax, ecx
    pop edi
    pop ecx
    pop ebx
    ret

.none_free:
    mov eax, -1
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; get_pipe - Get pointer to pipe structure
; Input: EAX = pipe index
; Returns: EAX = pointer to pipe, or 0 if invalid
; ============================================================================
global get_pipe
get_pipe:
    cmp eax, MAX_PIPES
    jge .invalid

    imul eax, PIPE_STRUCT_SIZE
    add eax, pipe_table
    ret

.invalid:
    xor eax, eax
    ret

; ============================================================================
; sys_pipe - Create a pipe (syscall)
; Input: [esp+4] = pointer to int32[2] for read/write FDs
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global sys_pipe
sys_pipe:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov edi, [esp + 24]     ; Pointer to FD array

    ; Create pipe
    call pipe_create
    cmp eax, -1
    je .error
    mov esi, eax            ; ESI = pipe index

    ; Allocate read FD
    call fd_alloc
    cmp eax, -1
    je .error
    mov ebx, eax            ; EBX = read FD

    ; Set up read FD entry
    mov eax, [current_pid]
    push ebx                ; Save read FD
    call get_fd_entry
    mov dword [eax], FD_PIPE_READ
    mov [eax + 4], esi      ; Pipe index
    pop ebx

    ; Allocate write FD
    call fd_alloc
    cmp eax, -1
    je .error
    mov ecx, eax            ; ECX = write FD

    ; Set up write FD entry
    mov eax, [current_pid]
    push ecx
    call get_fd_entry
    mov dword [eax], FD_PIPE_WRITE
    mov [eax + 4], esi      ; Pipe index
    pop ecx

    ; Update pipe with owning processes
    mov eax, esi
    call get_pipe
    mov edx, [current_pid]
    mov [eax + PIPE_READ_PID], edx
    mov [eax + PIPE_WRITE_PID], edx

    ; Store FDs in user array
    mov [edi], ebx          ; fds[0] = read
    mov [edi + 4], ecx      ; fds[1] = write

    xor eax, eax            ; Success
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

.error:
    mov eax, -1
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_read - Read from file descriptor
; Input:
;   [esp+4] = fd
;   [esp+8] = buffer
;   [esp+12] = count
; Returns: EAX = bytes read, or -1 on error
; ============================================================================
global sys_read
sys_read:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov ebx, [esp + 24]     ; FD
    mov edi, [esp + 28]     ; Buffer
    mov ecx, [esp + 32]     ; Count

    ; Get FD entry
    mov eax, [current_pid]
    call get_fd_entry
    test eax, eax
    jz .error
    mov esi, eax            ; ESI = FD entry

    ; Check FD type
    mov eax, [esi]
    cmp eax, FD_PIPE_READ
    je .read_pipe
    cmp eax, FD_TTY
    je .read_tty
    jmp .error

.read_pipe:
    ; Get pipe structure
    mov eax, [esi + 4]      ; Pipe index
    call get_pipe
    test eax, eax
    jz .error
    mov esi, eax            ; ESI = pipe

    ; Check if any data available
    mov edx, [esi + PIPE_COUNT]
    test edx, edx
    jz .pipe_empty

    ; Calculate bytes to read (min of count and available)
    cmp ecx, edx
    jle .count_ok
    mov ecx, edx
.count_ok:

    ; Copy data from pipe buffer
    push ecx                ; Save count
    mov edx, [esi + PIPE_READ_POS]
    lea esi, [esi + PIPE_BUFFER]
    add esi, edx            ; Source = buffer + read_pos

.copy_loop:
    test ecx, ecx
    jz .copy_done
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jmp .copy_loop

.copy_done:
    pop ecx                 ; Restore count

    ; Update pipe state
    mov eax, [esp + 24]     ; FD
    mov eax, [current_pid]
    mov ebx, [esp + 24]
    call get_fd_entry
    mov eax, [eax + 4]      ; Pipe index
    call get_pipe
    mov esi, eax

    ; Update read position (with wrap)
    mov eax, [esi + PIPE_READ_POS]
    add eax, ecx
    cmp eax, PIPE_BUF_SIZE
    jl .no_wrap
    sub eax, PIPE_BUF_SIZE
.no_wrap:
    mov [esi + PIPE_READ_POS], eax

    ; Decrease count
    sub [esi + PIPE_COUNT], ecx

    mov eax, ecx            ; Return bytes read
    jmp .done

.pipe_empty:
    xor eax, eax            ; Return 0 (no data, would block)
    jmp .done

.read_tty:
    ; Read from keyboard
    extern keyboard_available
    extern keyboard_read_char
    xor edx, edx            ; Bytes read

.tty_loop:
    test ecx, ecx
    jz .tty_done
    call keyboard_available
    test eax, eax
    jz .tty_done
    call keyboard_read_char
    mov [edi], al
    inc edi
    inc edx
    dec ecx
    jmp .tty_loop

.tty_done:
    mov eax, edx
    jmp .done

.error:
    mov eax, -1

.done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_write - Write to file descriptor
; Input:
;   [esp+4] = fd
;   [esp+8] = buffer
;   [esp+12] = count
; Returns: EAX = bytes written, or -1 on error
; ============================================================================
global sys_write
sys_write:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov ebx, [esp + 24]     ; FD
    mov esi, [esp + 28]     ; Buffer
    mov ecx, [esp + 32]     ; Count

    ; Get FD entry
    mov eax, [current_pid]
    call get_fd_entry
    test eax, eax
    jz .error
    mov edi, eax            ; EDI = FD entry

    ; Check FD type
    mov eax, [edi]
    cmp eax, FD_PIPE_WRITE
    je .write_pipe
    cmp eax, FD_TTY
    je .write_tty
    cmp eax, FD_DEV_NULL
    je .write_null
    jmp .error

.write_pipe:
    ; Get pipe structure
    mov eax, [edi + 4]      ; Pipe index
    call get_pipe
    test eax, eax
    jz .error
    mov edi, eax            ; EDI = pipe

    ; Check space available
    mov edx, PIPE_BUF_SIZE
    sub edx, [edi + PIPE_COUNT]
    test edx, edx
    jz .pipe_full

    ; Calculate bytes to write (min of count and space)
    cmp ecx, edx
    jle .space_ok
    mov ecx, edx
.space_ok:

    ; Copy data to pipe buffer
    push ecx                ; Save count
    mov edx, [edi + PIPE_WRITE_POS]
    lea edi, [edi + PIPE_BUFFER]
    add edi, edx            ; Dest = buffer + write_pos

.write_loop:
    test ecx, ecx
    jz .write_done
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jmp .write_loop

.write_done:
    pop ecx                 ; Restore count

    ; Update pipe state
    mov ebx, [esp + 24]     ; FD
    mov eax, [current_pid]
    call get_fd_entry
    mov eax, [eax + 4]      ; Pipe index
    call get_pipe
    mov edi, eax

    ; Update write position (with wrap)
    mov eax, [edi + PIPE_WRITE_POS]
    add eax, ecx
    cmp eax, PIPE_BUF_SIZE
    jl .no_wrap_w
    sub eax, PIPE_BUF_SIZE
.no_wrap_w:
    mov [edi + PIPE_WRITE_POS], eax

    ; Increase count
    add [edi + PIPE_COUNT], ecx

    mov eax, ecx            ; Return bytes written
    jmp .done

.pipe_full:
    xor eax, eax            ; Return 0 (would block)
    jmp .done

.write_tty:
    ; Write to serial/VGA
    extern serial_putchar
    push ecx

.tty_write_loop:
    test ecx, ecx
    jz .tty_write_done
    movzx eax, byte [esi]
    push eax
    call serial_putchar
    add esp, 4
    inc esi
    dec ecx
    jmp .tty_write_loop

.tty_write_done:
    pop eax                 ; Return count
    jmp .done

.write_null:
    mov eax, ecx            ; Accept all, write nothing
    jmp .done

.error:
    mov eax, -1

.done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_close - Close a file descriptor
; Input: [esp+4] = fd
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global sys_close
sys_close:
    push ebx
    push ecx

    mov ebx, [esp + 12]     ; FD

    ; Get FD entry
    mov eax, [current_pid]
    call get_fd_entry
    test eax, eax
    jz .error

    ; Check if it's a pipe - might need to clean up
    mov ecx, [eax]          ; Type
    cmp ecx, FD_PIPE_READ
    je .close_pipe
    cmp ecx, FD_PIPE_WRITE
    je .close_pipe

.clear_fd:
    ; Mark FD as unused
    mov dword [eax], FD_UNUSED
    mov dword [eax + 4], 0

    xor eax, eax
    pop ecx
    pop ebx
    ret

.close_pipe:
    push eax                ; Save FD entry pointer
    mov eax, [eax + 4]      ; Pipe index
    call get_pipe
    test eax, eax
    jz .pipe_done

    ; Clear the appropriate pid in pipe
    pop ecx                 ; Restore FD entry pointer
    push ecx
    cmp dword [ecx], FD_PIPE_READ
    jne .clear_write_pid
    mov dword [eax + PIPE_READ_PID], -1
    jmp .check_pipe_free

.clear_write_pid:
    mov dword [eax + PIPE_WRITE_PID], -1

.check_pipe_free:
    ; If both ends closed, free the pipe
    cmp dword [eax + PIPE_READ_PID], -1
    jne .pipe_done
    cmp dword [eax + PIPE_WRITE_PID], -1
    jne .pipe_done
    mov dword [eax + PIPE_FLAGS], 0     ; Free pipe

.pipe_done:
    pop eax                 ; Restore FD entry
    jmp .clear_fd

.error:
    mov eax, -1
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_dup - Duplicate a file descriptor
; Input: [esp+4] = old fd
; Returns: EAX = new fd, or -1 on error
; ============================================================================
global sys_dup
sys_dup:
    push ebx
    push ecx
    push edx

    mov ebx, [esp + 16]     ; Old FD

    ; Get old FD entry
    mov eax, [current_pid]
    call get_fd_entry
    test eax, eax
    jz .error
    mov edx, eax            ; EDX = old FD entry

    ; Check if valid
    cmp dword [edx], FD_UNUSED
    je .error

    ; Allocate new FD
    call fd_alloc
    cmp eax, -1
    je .error
    mov ecx, eax            ; ECX = new FD number

    ; Get new FD entry
    mov eax, [current_pid]
    mov ebx, ecx
    call get_fd_entry

    ; Copy FD entry
    mov ebx, [edx]          ; Type
    mov [eax], ebx
    mov ebx, [edx + 4]      ; Data
    mov [eax + 4], ebx

    mov eax, ecx            ; Return new FD
    pop edx
    pop ecx
    pop ebx
    ret

.error:
    mov eax, -1
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_dup2 - Duplicate FD to specific number
; Input:
;   [esp+4] = old fd
;   [esp+8] = new fd
; Returns: EAX = new fd, or -1 on error
; ============================================================================
global sys_dup2
sys_dup2:
    push ebx
    push ecx
    push edx
    push esi

    mov ebx, [esp + 20]     ; Old FD
    mov ecx, [esp + 24]     ; New FD

    ; Validate new FD number
    cmp ecx, MAX_FDS
    jge .error

    ; Get old FD entry
    mov eax, [current_pid]
    call get_fd_entry
    test eax, eax
    jz .error
    mov edx, eax            ; EDX = old FD entry

    ; Check if valid
    cmp dword [edx], FD_UNUSED
    je .error

    ; If old == new, just return new
    cmp ebx, ecx
    je .same

    ; Close new FD if open
    push edx
    push ecx
    push ecx
    call sys_close
    add esp, 4
    pop ecx
    pop edx

    ; Get new FD entry
    mov eax, [current_pid]
    mov ebx, ecx
    call get_fd_entry
    mov esi, eax            ; ESI = new FD entry

    ; Copy FD entry
    mov ebx, [edx]          ; Type
    mov [esi], ebx
    mov ebx, [edx + 4]      ; Data
    mov [esi + 4], ebx

.same:
    mov eax, ecx            ; Return new FD
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

.error:
    mov eax, -1
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; setup_std_fds - Set up stdin/stdout/stderr for a process
; Input: EAX = pid
; ============================================================================
global setup_std_fds
setup_std_fds:
    push ebx
    push ecx

    mov ecx, eax            ; Save PID

    ; FD 0 = stdin (TTY)
    mov eax, ecx
    mov ebx, 0
    call get_fd_entry
    mov dword [eax], FD_TTY
    mov dword [eax + 4], 0

    ; FD 1 = stdout (TTY)
    mov eax, ecx
    mov ebx, 1
    call get_fd_entry
    mov dword [eax], FD_TTY
    mov dword [eax + 4], 0

    ; FD 2 = stderr (TTY)
    mov eax, ecx
    mov ebx, 2
    call get_fd_entry
    mov dword [eax], FD_TTY
    mov dword [eax + 4], 0

    pop ecx
    pop ebx
    ret
