; process.asm - Process management and context switching for BrainhairOS
; Implements PCB, scheduler, and context switch

bits 32

; Process states
PROC_UNUSED   equ 0
PROC_READY    equ 1
PROC_RUNNING  equ 2
PROC_BLOCKED  equ 3
PROC_ZOMBIE   equ 4
PROC_STOPPED  equ 5   ; Stopped by signal (SIGSTOP/SIGTSTP)

; Process Control Block offsets (must match kernel_main.bh)
PCB_PID       equ 0    ; int32 - Process ID
PCB_STATE     equ 4    ; int32 - Process state
PCB_PARENT    equ 8    ; int32 - Parent PID
PCB_PRIORITY  equ 12   ; int32 - Priority (0 = highest)
; CPU Context (saved registers)
PCB_EAX       equ 16
PCB_EBX       equ 20
PCB_ECX       equ 24
PCB_EDX       equ 28
PCB_ESI       equ 32
PCB_EDI       equ 36
PCB_EBP       equ 40
PCB_ESP       equ 44
PCB_EIP       equ 48
PCB_EFLAGS    equ 52
; Memory
PCB_PAGE_DIR  equ 56   ; Physical address of page directory
PCB_STACK_TOP equ 60   ; Top of kernel stack
PCB_USER_ESP  equ 64   ; User stack pointer
; IPC
PCB_WAITING   equ 68   ; PID waiting for (-1 = any, 0 = none)
PCB_MSG_BUF   equ 72   ; Message buffer pointer
; Exit/wait support
PCB_EXIT_CODE equ 76   ; Exit code for zombie processes
PCB_WAIT_PID  equ 80   ; PID we're waiting for (-1 = any child, 0 = not waiting)
; User/group support
PCB_UID       equ 84   ; User ID (0 = root)
PCB_GID       equ 88   ; Group ID (0 = root/wheel)
PCB_EUID      equ 92   ; Effective User ID
PCB_EGID      equ 96   ; Effective Group ID
; Thread support
PCB_IS_THREAD equ 100  ; int32: 1 if thread, 0 if process
PCB_MAIN_PROC equ 104  ; int32: Main process PID (for threads)
PCB_THREAD_ID equ 108  ; int32: Thread ID within process (0 for main)
PCB_NEXT_TID  equ 112  ; int32: Next TID to assign (main process only)
PCB_PGRP      equ 116  ; int32: Process group ID
PCB_SID       equ 120  ; int32: Session ID
PCB_CTTY      equ 124  ; int32: Controlling TTY (-1 = none)
; Thread-local storage
PCB_TLS_BASE  equ 128  ; int32: TLS base pointer (user-space TLS area)
; Thread join support
PCB_THREAD_EXIT_STATUS equ 132  ; int32: Exit status when thread exits
PCB_THREAD_JOINED      equ 136  ; int32: 1 if thread has been joined, 0 otherwise
PCB_THREAD_JOINER      equ 140  ; int32: PID of thread waiting to join (0 = none)
PCB_THREAD_DETACHED    equ 144  ; int32: 1 if detached, 0 if joinable

PCB_SIZE      equ 148  ; Total size of PCB

; Maximum number of processes
MAX_PROCS     equ 16

section .data

; Current running process
global current_pid
current_pid:
    dd 0

; Next PID to assign
global next_pid
next_pid:
    dd 1

; Number of ready processes
global ready_count
ready_count:
    dd 0

; Scheduler tick counter
global tick_count
tick_count:
    dd 0

section .bss

; Process table (array of PCBs)
align 4096
global process_table
process_table:
    resb PCB_SIZE * MAX_PROCS

; Kernel stacks for processes (4KB each)
align 4096
global kernel_stacks
kernel_stacks:
    resb 4096 * MAX_PROCS

section .text

; External ELF loader functions (for exec)
extern elf_validate
extern elf_get_entry
extern elf_load

; External paging symbols
extern page_directory

; ============================================================================
; init_scheduler - Initialize the scheduler
; ============================================================================
global init_scheduler
init_scheduler:
    push eax
    push ecx
    push edi

    ; Clear process table
    mov edi, process_table
    mov ecx, PCB_SIZE * MAX_PROCS / 4
    xor eax, eax
    rep stosd

    ; Initialize current_pid to 0 (kernel)
    mov dword [current_pid], 0
    mov dword [next_pid], 1
    mov dword [ready_count], 1   ; Kernel is ready/running
    mov dword [tick_count], 0

    ; Register kernel as process 0 (RUNNING state)
    mov edi, process_table
    mov dword [edi + PCB_PID], 0
    mov dword [edi + PCB_STATE], PROC_RUNNING
    mov dword [edi + PCB_PARENT], 0
    mov dword [edi + PCB_PRIORITY], 0
    ; Set kernel's page directory for thread inheritance
    mov eax, page_directory
    mov [edi + PCB_PAGE_DIR], eax
    ; Initialize thread fields
    mov dword [edi + PCB_IS_THREAD], 0
    mov dword [edi + PCB_THREAD_ID], 0
    mov dword [edi + PCB_NEXT_TID], 1  ; First thread will get TID 1
    ; Kernel uses its own stack, no need to set stack pointers

    pop edi
    pop ecx
    pop eax
    ret

; ============================================================================
; get_pcb - Get PCB pointer for a PID
; Input: EAX = PID
; Returns: EAX = pointer to PCB, or 0 if invalid
; ============================================================================
global get_pcb
get_pcb:
    cmp eax, MAX_PROCS
    jge .invalid

    ; Calculate offset: process_table + (pid * PCB_SIZE)
    imul eax, PCB_SIZE
    add eax, process_table
    ret

.invalid:
    xor eax, eax
    ret

; ============================================================================
; create_process - Create a new process
; Input:
;   [esp+4] = entry point (EIP)
;   [esp+8] = parent PID
; Returns: EAX = new PID, or -1 on failure
; ============================================================================
global create_process
create_process:
    push ebx
    push ecx
    push edx
    push edi

    ; Find a free slot in process table
    mov ecx, 0              ; Start from PID 0
    mov edi, process_table

.find_slot:
    cmp ecx, MAX_PROCS
    jge .no_slots

    mov eax, [edi + PCB_STATE]
    cmp eax, PROC_UNUSED
    je .found_slot

    add edi, PCB_SIZE
    inc ecx
    jmp .find_slot

.found_slot:
    ; ECX = PID, EDI = PCB pointer

    ; Set up PCB
    mov [edi + PCB_PID], ecx
    mov dword [edi + PCB_STATE], PROC_READY
    mov eax, [esp + 24]     ; Parent PID
    mov [edi + PCB_PARENT], eax
    mov dword [edi + PCB_PRIORITY], 0

    ; Set up entry point
    mov eax, [esp + 20]     ; Entry point
    mov [edi + PCB_EIP], eax

    ; Set up kernel stack
    ; Stack top = kernel_stacks + ((pid + 1) * 4096)
    mov eax, ecx
    inc eax
    shl eax, 12             ; * 4096
    add eax, kernel_stacks
    mov [edi + PCB_STACK_TOP], eax
    mov [edi + PCB_ESP], eax

    ; Set default EFLAGS (interrupts enabled)
    mov dword [edi + PCB_EFLAGS], 0x202

    ; Use same page directory as kernel for now
    mov eax, cr3
    mov [edi + PCB_PAGE_DIR], eax

    ; Clear other registers
    xor eax, eax
    mov [edi + PCB_EAX], eax
    mov [edi + PCB_EBX], eax
    mov [edi + PCB_ECX], eax
    mov [edi + PCB_EDX], eax
    mov [edi + PCB_ESI], eax
    mov [edi + PCB_EDI], eax
    mov [edi + PCB_EBP], eax

    ; Initialize UID/GID (default to root)
    xor eax, eax
    mov [edi + PCB_UID], eax
    mov [edi + PCB_GID], eax
    mov [edi + PCB_EUID], eax
    mov [edi + PCB_EGID], eax

    ; Increment ready count
    inc dword [ready_count]

    ; Return PID
    mov eax, ecx

    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

.no_slots:
    mov eax, -1
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; fork - Create a copy of the current process
; Returns: EAX = child PID to parent, 0 to child, -1 on error
; ============================================================================
global fork
fork:
    push ebx
    push ecx
    push edx
    push esi
    push edi
    push ebp

    ; Find a free slot in process table
    mov ecx, 1              ; Start from PID 1 (0 is kernel)
    mov edi, process_table
    add edi, PCB_SIZE       ; Skip kernel's PCB

.fork_find_slot:
    cmp ecx, MAX_PROCS
    jge .fork_no_slots

    mov eax, [edi + PCB_STATE]
    cmp eax, PROC_UNUSED
    je .fork_found_slot

    add edi, PCB_SIZE
    inc ecx
    jmp .fork_find_slot

.fork_found_slot:
    ; ECX = child PID, EDI = child PCB pointer
    push ecx                ; Save child PID
    push edi                ; Save child PCB pointer

    ; Get parent PCB
    mov eax, [current_pid]
    call get_pcb
    mov esi, eax            ; ESI = parent PCB

    ; Copy parent PCB to child
    pop edi                 ; Restore child PCB
    push edi                ; Save again
    mov ecx, PCB_SIZE / 4
    rep movsd

    ; Restore pointers
    pop edi                 ; Child PCB
    pop ecx                 ; Child PID

    ; Set child-specific fields
    mov [edi + PCB_PID], ecx
    mov dword [edi + PCB_STATE], PROC_READY
    mov eax, [current_pid]
    mov [edi + PCB_PARENT], eax

    ; Set up child's kernel stack (separate from parent)
    mov eax, ecx
    inc eax
    shl eax, 12             ; * 4096
    add eax, kernel_stacks
    mov [edi + PCB_STACK_TOP], eax
    mov [edi + PCB_ESP], eax

    ; Child returns 0 from fork
    mov dword [edi + PCB_EAX], 0

    ; Set child's EIP to return address (after fork call)
    ; Get return address from our stack frame
    mov eax, [esp + 24]     ; Return address (after pushed regs)
    mov [edi + PCB_EIP], eax

    ; Clear wait status
    mov dword [edi + PCB_WAIT_PID], 0
    mov dword [edi + PCB_EXIT_CODE], 0

    ; Increment ready count
    inc dword [ready_count]

    ; Parent returns child PID
    mov eax, ecx

    pop ebp
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

.fork_no_slots:
    mov eax, -1
    pop ebp
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_exec - Replace current process image with new program
; Input:
;   [esp+4] = pointer to ELF image in memory
;   [esp+8] = argument string pointer (can be 0)
; Returns: -1 on error, does not return on success
; ============================================================================
global sys_exec
sys_exec:
    push ebx
    push ecx
    push edx
    push esi
    push edi
    push ebp

    ; Get parameters
    mov esi, [esp + 28]     ; ELF pointer
    mov ebx, [esp + 32]     ; argv (unused for now)

    ; Validate ELF
    push esi
    call elf_validate
    add esp, 4
    test eax, eax
    jz .exec_error

    ; Get entry point
    push esi
    call elf_get_entry
    add esp, 4
    mov ebx, eax            ; Save entry point in EBX

    ; Load ELF segments (use virtual addresses from ELF)
    push dword 0            ; dest_base = 0 (use vaddr)
    push esi                ; ELF pointer
    call elf_load
    add esp, 8
    test eax, eax
    jz .exec_error

    ; Get current process PCB
    mov ecx, [current_pid]
    mov eax, ecx
    imul eax, PCB_SIZE
    add eax, process_table
    mov edi, eax            ; EDI = current PCB

    ; Reset process state
    mov [edi + PCB_EIP], ebx        ; New entry point

    ; Reset stack to top
    mov eax, ecx
    inc eax
    shl eax, 12             ; * 4096
    add eax, kernel_stacks
    mov [edi + PCB_STACK_TOP], eax
    mov [edi + PCB_ESP], eax

    ; Clear registers
    xor eax, eax
    mov [edi + PCB_EAX], eax
    mov [edi + PCB_EBX], eax
    mov [edi + PCB_ECX], eax
    mov [edi + PCB_EDX], eax
    mov [edi + PCB_ESI], eax
    mov [edi + PCB_EDI], eax
    mov [edi + PCB_EBP], eax

    ; Reset EFLAGS
    mov dword [edi + PCB_EFLAGS], 0x202

    ; Now we need to "return" to the new program
    ; This is done by restoring the new context
    ; Set up stack for iret/context switch

    ; Load new stack pointer
    mov esp, [edi + PCB_ESP]

    ; Push return context for the new program
    ; We'll jump directly to the entry point
    mov eax, [edi + PCB_EIP]
    jmp eax                 ; Jump to new program entry point

    ; Should never reach here

.exec_error:
    mov eax, -1
    pop ebp
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; sys_execve - exec with path resolution (for filesystem programs)
; Input:
;   [esp+4] = path string pointer
;   [esp+8] = argv array pointer
;   [esp+12] = envp array pointer
; Returns: -1 on error, does not return on success
; ============================================================================
global sys_execve
sys_execve:
    ; For now, just return error - filesystem exec not implemented yet
    mov eax, -1
    ret

; ============================================================================
; sys_getuid - Get real user ID
; Returns: EAX = UID
; ============================================================================
global sys_getuid
sys_getuid:
    mov eax, [current_pid]
    call get_pcb
    mov eax, [eax + PCB_UID]
    ret

; ============================================================================
; sys_getgid - Get real group ID
; Returns: EAX = GID
; ============================================================================
global sys_getgid
sys_getgid:
    mov eax, [current_pid]
    call get_pcb
    mov eax, [eax + PCB_GID]
    ret

; ============================================================================
; sys_geteuid - Get effective user ID
; Returns: EAX = EUID
; ============================================================================
global sys_geteuid
sys_geteuid:
    mov eax, [current_pid]
    call get_pcb
    mov eax, [eax + PCB_EUID]
    ret

; ============================================================================
; sys_getegid - Get effective group ID
; Returns: EAX = EGID
; ============================================================================
global sys_getegid
sys_getegid:
    mov eax, [current_pid]
    call get_pcb
    mov eax, [eax + PCB_EGID]
    ret

; ============================================================================
; sys_setuid - Set user ID (only root can do this)
; Input: [esp+4] = new UID
; Returns: 0 on success, -1 on error
; ============================================================================
global sys_setuid
sys_setuid:
    push ebx
    mov eax, [current_pid]
    call get_pcb
    mov ebx, eax            ; EBX = current PCB

    ; Check if root (EUID == 0)
    mov eax, [ebx + PCB_EUID]
    test eax, eax
    jnz .setuid_fail        ; Not root, cannot setuid

    ; Set UID
    mov eax, [esp + 8]      ; New UID
    mov [ebx + PCB_UID], eax
    mov [ebx + PCB_EUID], eax
    xor eax, eax            ; Return 0
    pop ebx
    ret

.setuid_fail:
    mov eax, -1
    pop ebx
    ret

; ============================================================================
; sys_setgid - Set group ID (only root can do this)
; Input: [esp+4] = new GID
; Returns: 0 on success, -1 on error
; ============================================================================
global sys_setgid
sys_setgid:
    push ebx
    mov eax, [current_pid]
    call get_pcb
    mov ebx, eax            ; EBX = current PCB

    ; Check if root (EUID == 0)
    mov eax, [ebx + PCB_EUID]
    test eax, eax
    jnz .setgid_fail        ; Not root, cannot setgid

    ; Set GID
    mov eax, [esp + 8]      ; New GID
    mov [ebx + PCB_GID], eax
    mov [ebx + PCB_EGID], eax
    xor eax, eax            ; Return 0
    pop ebx
    ret

.setgid_fail:
    mov eax, -1
    pop ebx
    ret

; ============================================================================
; schedule - Select next process to run (round-robin)
; Returns: EAX = PID of next process to run
; ============================================================================
global schedule
schedule:
    push ebx
    push ecx
    push edi

    ; Start from current_pid + 1
    mov ecx, [current_pid]
    inc ecx
    mov ebx, 0              ; Loop counter

.find_ready:
    ; Wrap around
    cmp ecx, MAX_PROCS
    jl .check_proc
    xor ecx, ecx

.check_proc:
    ; Check if we've searched all processes
    cmp ebx, MAX_PROCS
    jge .no_ready

    ; Get PCB
    mov eax, ecx
    call get_pcb
    test eax, eax
    jz .next

    mov edi, eax

    ; Check if READY
    mov eax, [edi + PCB_STATE]
    cmp eax, PROC_READY
    je .found

.next:
    inc ecx
    inc ebx
    jmp .find_ready

.found:
    mov eax, ecx
    pop edi
    pop ecx
    pop ebx
    ret

.no_ready:
    ; No ready process, return current or 0
    mov eax, [current_pid]
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; context_switch - Switch from current process to new process
; Input: [esp+4] = PID of new process
; ============================================================================
global context_switch
context_switch:
    ; Save current process state
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .load_new            ; No current process

    mov edi, eax            ; EDI = current PCB

    ; Save registers
    mov [edi + PCB_EAX], eax
    mov [edi + PCB_EBX], ebx
    mov [edi + PCB_ECX], ecx
    mov [edi + PCB_EDX], edx
    mov [edi + PCB_ESI], esi
    mov [edi + PCB_EBP], ebp

    ; Save return address as EIP
    mov eax, [esp]
    mov [edi + PCB_EIP], eax

    ; Save ESP+4 (skip return addr, so ESP points to arg after restore+ret)
    mov eax, esp
    add eax, 4
    mov [edi + PCB_ESP], eax

    ; Save EFLAGS
    pushfd
    pop eax
    mov [edi + PCB_EFLAGS], eax

    ; Mark as READY (unless blocked/zombie)
    mov eax, [edi + PCB_STATE]
    cmp eax, PROC_RUNNING
    jne .load_new
    mov dword [edi + PCB_STATE], PROC_READY

.load_new:
    ; Get new process PCB
    mov eax, [esp + 4]      ; New PID
    mov [current_pid], eax
    call get_pcb
    test eax, eax
    jz .fail

    mov edi, eax            ; EDI = new PCB

    ; Mark as RUNNING
    mov dword [edi + PCB_STATE], PROC_RUNNING

    ; Load page directory
    mov eax, [edi + PCB_PAGE_DIR]
    mov cr3, eax

    ; Load registers
    mov eax, [edi + PCB_EFLAGS]
    push eax
    popfd

    mov ebx, [edi + PCB_EBX]
    mov ecx, [edi + PCB_ECX]
    mov edx, [edi + PCB_EDX]
    mov esi, [edi + PCB_ESI]
    mov ebp, [edi + PCB_EBP]
    mov esp, [edi + PCB_ESP]

    ; Jump to new process
    mov eax, [edi + PCB_EIP]
    push eax
    mov eax, [edi + PCB_EAX]
    ret                     ; Jump to EIP

.fail:
    ; Should never happen - halt
    cli
    hlt

; ============================================================================
; yield - Voluntarily give up CPU
; ============================================================================
global yield
yield:
    ; Find next ready process
    call schedule

    ; If same as current, just return
    cmp eax, [current_pid]
    je .done

    ; Switch to new process
    push eax
    call context_switch
    add esp, 4

.done:
    ret

; ============================================================================
; exit_process - Terminate current process
; Input: [esp+4] = exit code
; ============================================================================
global exit_process
exit_process:
    push ebx
    push esi

    ; Get current PCB
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .halt

    mov edi, eax

    ; Save exit code
    mov eax, [esp + 12]         ; Exit code (accounting for pushed regs)
    mov [edi + PCB_EXIT_CODE], eax

    ; Mark as ZOMBIE
    mov dword [edi + PCB_STATE], PROC_ZOMBIE

    ; Decrement ready count
    dec dword [ready_count]

    ; Get our parent PID
    mov ebx, [edi + PCB_PARENT]

    ; Check if parent is waiting for us
    mov eax, ebx
    call get_pcb
    test eax, eax
    jz .no_parent

    mov esi, eax                ; ESI = parent PCB

    ; Check if parent is blocked waiting
    mov eax, [esi + PCB_STATE]
    cmp eax, PROC_BLOCKED
    jne .no_parent

    ; Check if parent is waiting for us specifically or any child (-1)
    mov eax, [esi + PCB_WAIT_PID]
    cmp eax, 0
    je .no_parent               ; Not waiting for anyone
    cmp eax, -1
    je .wake_parent             ; Waiting for any child
    cmp eax, [current_pid]
    jne .no_parent              ; Not waiting for us

.wake_parent:
    ; Wake up the parent
    mov dword [esi + PCB_STATE], PROC_READY
    inc dword [ready_count]

.no_parent:
    ; Schedule next process
    call schedule

    ; Switch to it
    push eax
    call context_switch
    ; Never returns

.halt:
    cli
    hlt

; ============================================================================
; waitpid - Wait for a child process to exit
; Input:
;   [esp+4] = PID to wait for (-1 = any child)
; Returns: EAX = PID of exited child, or -1 on error
;          [esp+8] = pointer to store exit status (or NULL)
; ============================================================================
global waitpid
waitpid:
    push ebx
    push ecx
    push edi
    push esi

    mov ebx, [esp + 20]         ; PID to wait for
    mov esi, [esp + 24]         ; Status pointer (may be NULL)

    ; Get current PCB
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .error

    mov edi, eax                ; EDI = our PCB

.check_children:
    ; Look for zombie children
    mov ecx, 0                  ; Start from PID 0

.scan_loop:
    cmp ecx, MAX_PROCS
    jge .no_zombie_found

    ; Get PCB for this PID
    mov eax, ecx
    push ecx
    call get_pcb
    pop ecx
    test eax, eax
    jz .next_child

    ; Check if this is our child
    push eax
    mov eax, [eax + PCB_PARENT]
    cmp eax, [current_pid]
    pop eax
    jne .next_child

    ; Check if it's a zombie
    cmp dword [eax + PCB_STATE], PROC_ZOMBIE
    jne .next_child

    ; Check if we're waiting for this specific child or any child
    cmp ebx, -1
    je .found_zombie            ; Waiting for any
    cmp ebx, ecx
    je .found_zombie            ; Waiting for this one

.next_child:
    inc ecx
    jmp .scan_loop

.found_zombie:
    ; ECX = child PID, EAX = child PCB
    push ecx                    ; Save child PID

    ; Get exit code
    mov ebx, [eax + PCB_EXIT_CODE]

    ; Store exit status if pointer provided
    test esi, esi
    jz .no_status
    mov [esi], ebx

.no_status:
    ; Free the child's PCB (mark as UNUSED)
    mov dword [eax + PCB_STATE], PROC_UNUSED
    mov dword [eax + PCB_PID], 0

    ; Return child PID
    pop eax

    pop esi
    pop edi
    pop ecx
    pop ebx
    ret

.no_zombie_found:
    ; No zombie children yet - check if we have any children at all
    mov ecx, 0
    xor eax, eax                ; Child count

.count_children:
    cmp ecx, MAX_PROCS
    jge .done_counting

    push eax
    mov eax, ecx
    push ecx
    call get_pcb
    pop ecx
    mov edx, eax
    pop eax

    test edx, edx
    jz .count_next

    ; Check if this is our child and not unused
    cmp dword [edx + PCB_STATE], PROC_UNUSED
    je .count_next
    push eax
    mov eax, [edx + PCB_PARENT]
    cmp eax, [current_pid]
    pop eax
    jne .count_next

    ; Check if waiting for specific child
    cmp ebx, -1
    je .has_child
    cmp ebx, ecx
    jne .count_next

.has_child:
    inc eax

.count_next:
    inc ecx
    jmp .count_children

.done_counting:
    test eax, eax
    jz .error                   ; No children to wait for

    ; Block ourselves waiting for child
    mov dword [edi + PCB_STATE], PROC_BLOCKED
    mov [edi + PCB_WAIT_PID], ebx
    dec dword [ready_count]

    ; Schedule another process
    call schedule

    ; Context switch
    push eax
    call context_switch
    add esp, 4

    ; We're back - a child must have exited
    jmp .check_children

.error:
    mov eax, -1
    pop esi
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; timer_tick - Called by timer interrupt to potentially reschedule
; ============================================================================
global timer_tick
timer_tick:
    ; Increment tick count
    inc dword [tick_count]

    ; Preemptive scheduling disabled - context switch from interrupt
    ; is not properly implemented (corrupts interrupt return frame)
    ; Use cooperative scheduling via yield() instead

    ret

; ============================================================================
; get_current_pid - Get PID of current process
; Returns: EAX = current PID
; ============================================================================
global get_current_pid
get_current_pid:
    mov eax, [current_pid]
    ret

; ============================================================================
; getppid - Get parent PID of current process
; Returns: EAX = parent PID
; ============================================================================
global getppid
getppid:
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .no_parent
    mov eax, [eax + PCB_PARENT]
    ret
.no_parent:
    xor eax, eax
    ret

; ============================================================================
; get_tick_count - Get current timer tick count
; Returns: EAX = tick count
; ============================================================================
global get_tick_count
get_tick_count:
    mov eax, [tick_count]
    ret

; ============================================================================
; set_process_state - Set state of a process
; Input:
;   [esp+4] = PID
;   [esp+8] = new state
; ============================================================================
global set_process_state
set_process_state:
    push ebx

    mov eax, [esp + 8]      ; PID
    call get_pcb
    test eax, eax
    jz .done

    mov ebx, [esp + 12]     ; New state
    mov [eax + PCB_STATE], ebx

.done:
    pop ebx
    ret

; ============================================================================
; get_process_state - Get state of a process
; Input: [esp+4] = PID
; Returns: EAX = state (0=unused, 1=ready, 2=running, 3=blocked, 4=zombie)
;          or -1 if invalid PID
; ============================================================================
global get_process_state
get_process_state:
    mov eax, [esp + 4]      ; PID
    call get_pcb
    test eax, eax
    jz .invalid

    mov eax, [eax + PCB_STATE]
    ret

.invalid:
    mov eax, -1
    ret

; ============================================================================
; KERNEL THREADING SUPPORT
; ============================================================================

; ============================================================================
; thread_create - Create a new kernel thread
; Input:
;   [esp+4] = entry point (function pointer)
;   [esp+8] = user argument (passed to entry in EAX)
; Returns: EAX = thread PID on success, -1 on failure
; ============================================================================
global thread_create
thread_create:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    ; Get current process (to become main process if not already a thread)
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .fail
    mov esi, eax                ; ESI = current PCB

    ; If current is a thread, get the main process
    mov eax, [esi + PCB_IS_THREAD]
    test eax, eax
    jz .use_current_as_main
    ; Current is a thread, get main process PCB
    mov eax, [esi + PCB_MAIN_PROC]
    call get_pcb
    test eax, eax
    jz .fail
    mov esi, eax                ; ESI = main process PCB
.use_current_as_main:

    ; Find a free PCB slot
    xor ecx, ecx                ; ECX = slot index
    mov edi, process_table      ; EDI = process table
.find_slot:
    cmp ecx, MAX_PROCS
    jge .fail
    cmp dword [edi + PCB_STATE], PROC_UNUSED
    je .found_slot
    add edi, PCB_SIZE
    inc ecx
    jmp .find_slot

.found_slot:
    ; EDI = free PCB slot, ECX = slot index

    ; Allocate new PID
    mov eax, [next_pid]
    mov [edi + PCB_PID], eax
    inc dword [next_pid]

    ; Set as thread
    mov dword [edi + PCB_IS_THREAD], 1

    ; Set main process PID
    mov eax, [esi + PCB_PID]
    mov [edi + PCB_MAIN_PROC], eax

    ; Allocate thread ID from main process
    mov eax, [esi + PCB_NEXT_TID]
    mov [edi + PCB_THREAD_ID], eax
    inc dword [esi + PCB_NEXT_TID]

    ; Set state to READY
    mov dword [edi + PCB_STATE], PROC_READY

    ; Copy parent PID from main process
    mov eax, [esi + PCB_PARENT]
    mov [edi + PCB_PARENT], eax

    ; Copy user/group IDs from main process
    mov eax, [esi + PCB_UID]
    mov [edi + PCB_UID], eax
    mov eax, [esi + PCB_GID]
    mov [edi + PCB_GID], eax
    mov eax, [esi + PCB_EUID]
    mov [edi + PCB_EUID], eax
    mov eax, [esi + PCB_EGID]
    mov [edi + PCB_EGID], eax

    ; Copy process group and session from main
    mov eax, [esi + PCB_PGRP]
    mov [edi + PCB_PGRP], eax
    mov eax, [esi + PCB_SID]
    mov [edi + PCB_SID], eax
    mov eax, [esi + PCB_CTTY]
    mov [edi + PCB_CTTY], eax

    ; CRITICAL: Share page directory with main process
    mov eax, [esi + PCB_PAGE_DIR]
    mov [edi + PCB_PAGE_DIR], eax

    ; Set up kernel stack for this thread
    ; Stack is at kernel_stacks + slot_index * 4096 + 4096 (top)
    mov eax, ecx
    shl eax, 12                 ; * 4096
    add eax, kernel_stacks
    add eax, 4096               ; Top of stack
    mov [edi + PCB_STACK_TOP], eax

    ; Set up initial stack frame for thread
    ; Stack layout for new thread (stack grows down):
    ;   [esp+0] = thread_exit_trampoline (return address for when entry func returns)
    ;   [esp+4] = user argument (first param to entry function)
    ; Memory layout (higher addresses first):
    ;   stack_top - 4: user argument
    ;   stack_top - 8: thread_exit_trampoline  <- ESP points here
    mov ebx, eax                ; EBX = stack top
    sub ebx, 4
    mov eax, [esp + 28]         ; User argument (esp+8 + 5*4 pushes)
    mov [ebx], eax              ; [stack_top-4] = argument
    sub ebx, 4
    mov dword [ebx], thread_exit_trampoline  ; [stack_top-8] = return addr

    ; Thread starts with stack pointing to return address
    mov [edi + PCB_ESP], ebx

    ; Set entry point
    mov eax, [esp + 24]         ; Entry point (esp+4 + 5*4 pushes)
    mov [edi + PCB_EIP], eax

    ; Initialize other registers to 0
    xor eax, eax
    mov [edi + PCB_EAX], eax
    mov [edi + PCB_EBX], eax
    mov [edi + PCB_ECX], eax
    mov [edi + PCB_EDX], eax
    mov [edi + PCB_ESI], eax
    mov [edi + PCB_EDI], eax
    mov [edi + PCB_EBP], eax
    mov dword [edi + PCB_EFLAGS], 0x202 ; IF=1, reserved=1

    ; Initialize other fields
    mov dword [edi + PCB_PRIORITY], 0
    mov dword [edi + PCB_WAITING], 0
    mov dword [edi + PCB_MSG_BUF], 0
    mov dword [edi + PCB_EXIT_CODE], 0
    mov dword [edi + PCB_WAIT_PID], 0
    mov dword [edi + PCB_USER_ESP], 0

    ; Initialize thread join fields
    mov dword [edi + PCB_THREAD_EXIT_STATUS], 0
    mov dword [edi + PCB_THREAD_JOINED], 0
    mov dword [edi + PCB_THREAD_JOINER], 0
    mov dword [edi + PCB_THREAD_DETACHED], 0

    ; Increment ready count
    inc dword [ready_count]

    ; Return thread PID
    mov eax, [edi + PCB_PID]
    jmp .done

.fail:
    mov eax, -1

.done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; thread_exit_trampoline - Called when thread function returns
; Automatically calls thread_exit with return value
; ============================================================================
thread_exit_trampoline:
    ; EAX contains return value from thread function
    push eax
    call thread_exit
    ; thread_exit never returns

; ============================================================================
; thread_exit - Exit current thread
; Input: [esp+4] = exit code
; Note: If called from main process, calls exit_process instead
; ============================================================================
global thread_exit
thread_exit:
    ; Get current PCB
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .schedule_next           ; Shouldn't happen

    ; Check if this is a thread
    cmp dword [eax + PCB_IS_THREAD], 1
    jne .exit_process           ; Not a thread, exit whole process

    mov edi, eax                ; EDI = thread PCB

    ; Save exit status
    mov ebx, [esp + 4]          ; Exit code
    mov [edi + PCB_THREAD_EXIT_STATUS], ebx

    ; Check if thread is detached
    cmp dword [edi + PCB_THREAD_DETACHED], 1
    je .cleanup_detached

    ; Check if someone is waiting to join
    mov esi, [edi + PCB_THREAD_JOINER]
    test esi, esi
    jz .become_zombie

    ; Wake up the joiner - set its state to READY
    mov eax, esi
    call get_pcb
    test eax, eax
    jz .become_zombie
    mov dword [eax + PCB_STATE], PROC_READY
    jmp .cleanup_thread

.become_zombie:
    ; No joiner yet - become zombie so join can get exit status
    mov dword [edi + PCB_STATE], PROC_ZOMBIE
    dec dword [ready_count]
    jmp .schedule_next

.cleanup_detached:
    ; Detached thread - clean up immediately
.cleanup_thread:
    ; Mark thread as unused
    mov dword [edi + PCB_STATE], PROC_UNUSED
    mov dword [edi + PCB_IS_THREAD], 0
    mov dword [edi + PCB_MAIN_PROC], 0
    mov dword [edi + PCB_THREAD_ID], 0

    ; Decrement ready count
    dec dword [ready_count]

.schedule_next:
    ; Schedule next process/thread
    call schedule
    mov [current_pid], eax
    call get_pcb
    test eax, eax
    jz .halt                    ; No processes left

    ; Switch to next process
    jmp switch_to_process

.exit_process:
    ; Not a thread, delegate to process exit
    mov eax, [esp + 4]          ; Exit code
    push eax
    call exit_process
    ; exit_process doesn't return
    add esp, 4

.halt:
    cli
    hlt
    jmp .halt

; ============================================================================
; thread_yield - Yield CPU to another thread/process
; ============================================================================
global thread_yield
thread_yield:
    ; Save current context and switch
    call yield
    ret

; ============================================================================
; get_thread_id - Get current thread ID
; Returns: EAX = thread ID (0 for main process)
; ============================================================================
global get_thread_id
get_thread_id:
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .not_thread
    mov eax, [eax + PCB_THREAD_ID]
    ret
.not_thread:
    xor eax, eax
    ret

; ============================================================================
; is_thread - Check if current execution context is a thread
; Returns: EAX = 1 if thread, 0 if main process
; ============================================================================
global is_thread
is_thread:
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .not_thread
    mov eax, [eax + PCB_IS_THREAD]
    ret
.not_thread:
    xor eax, eax
    ret

; ============================================================================
; set_tls_base - Set TLS base pointer for current thread
; Args: [esp+4] = base address
; Returns: EAX = 0 on success
; ============================================================================
global set_tls_base
set_tls_base:
    push ebx
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .set_tls_fail
    mov ebx, [esp + 8]          ; Get base address argument
    mov [eax + PCB_TLS_BASE], ebx
    xor eax, eax                ; Return 0 = success
    pop ebx
    ret
.set_tls_fail:
    mov eax, -1
    pop ebx
    ret

; ============================================================================
; get_tls_base - Get TLS base pointer for current thread
; Returns: EAX = TLS base address (0 if not set)
; ============================================================================
global get_tls_base
get_tls_base:
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .get_tls_none
    mov eax, [eax + PCB_TLS_BASE]
    ret
.get_tls_none:
    xor eax, eax
    ret

; ============================================================================
; get_main_process - Get main process PID for current thread
; Returns: EAX = main process PID (or current PID if not a thread)
; ============================================================================
global get_main_process
get_main_process:
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .return_current
    cmp dword [eax + PCB_IS_THREAD], 1
    jne .return_current
    mov eax, [eax + PCB_MAIN_PROC]
    ret
.return_current:
    mov eax, [current_pid]
    ret

; ============================================================================
; thread_join - Wait for a thread to exit and get its exit status
; Input:
;   [esp+4] = thread PID to wait for
;   [esp+8] = pointer to store exit status (or 0 if not needed)
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global thread_join
thread_join:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    ; Get target thread PID
    mov esi, [esp + 24]         ; Thread PID (esp+4 + 5*4 pushes)
    mov edi, [esp + 28]         ; Status pointer (esp+8 + 5*4 pushes)

    ; Get target thread PCB
    mov eax, esi
    call get_pcb
    test eax, eax
    jz .error                   ; Invalid PID
    mov ebx, eax                ; EBX = target thread PCB

    ; Verify it's a thread
    cmp dword [ebx + PCB_IS_THREAD], 1
    jne .error

    ; Check if already joined
    cmp dword [ebx + PCB_THREAD_JOINED], 1
    je .error                   ; Already joined

    ; Check if detached
    cmp dword [ebx + PCB_THREAD_DETACHED], 1
    je .error                   ; Can't join detached thread

    ; Check thread state
    mov ecx, [ebx + PCB_STATE]
    cmp ecx, PROC_ZOMBIE
    je .already_exited          ; Thread already finished

    cmp ecx, PROC_UNUSED
    je .error                   ; Thread doesn't exist

    ; Thread is still running - block and wait
    ; Set ourselves as the joiner
    mov eax, [current_pid]
    mov [ebx + PCB_THREAD_JOINER], eax

    ; Block current thread
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .error
    mov dword [eax + PCB_STATE], PROC_BLOCKED

    ; Decrement ready count
    dec dword [ready_count]

    ; Switch to another thread/process
    call schedule
    mov [current_pid], eax
    call get_pcb
    test eax, eax
    jz .error

    ; When we wake up, the thread has exited
    ; Re-get the target thread PCB
    mov eax, esi
    call get_pcb
    test eax, eax
    jz .error
    mov ebx, eax

.already_exited:
    ; Get exit status
    mov ecx, [ebx + PCB_THREAD_EXIT_STATUS]

    ; Store exit status if pointer provided
    test edi, edi
    jz .no_status
    mov [edi], ecx

.no_status:
    ; Mark as joined
    mov dword [ebx + PCB_THREAD_JOINED], 1

    ; Clean up the thread PCB
    mov dword [ebx + PCB_STATE], PROC_UNUSED
    mov dword [ebx + PCB_IS_THREAD], 0
    mov dword [ebx + PCB_MAIN_PROC], 0
    mov dword [ebx + PCB_THREAD_ID], 0

    ; Success
    xor eax, eax
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
; thread_detach - Mark a thread as detached (auto-cleanup on exit)
; Input: [esp+4] = thread PID to detach
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global thread_detach
thread_detach:
    push ebx
    push esi

    ; Get target thread PID
    mov esi, [esp + 12]         ; Thread PID (esp+4 + 2*4 pushes)

    ; Get target thread PCB
    mov eax, esi
    call get_pcb
    test eax, eax
    jz .error                   ; Invalid PID
    mov ebx, eax                ; EBX = target thread PCB

    ; Verify it's a thread
    cmp dword [ebx + PCB_IS_THREAD], 1
    jne .error

    ; Check if already joined
    cmp dword [ebx + PCB_THREAD_JOINED], 1
    je .error                   ; Can't detach after join

    ; Mark as detached
    mov dword [ebx + PCB_THREAD_DETACHED], 1

    ; Success
    xor eax, eax
    jmp .done

.error:
    mov eax, -1

.done:
    pop esi
    pop ebx
    ret

; ============================================================================
; switch_to_process - Switch to process with PCB in EAX
; This is a low-level helper used by thread_exit
; ============================================================================
switch_to_process:
    mov edi, eax                ; EDI = target PCB

    ; Mark as running
    mov dword [edi + PCB_STATE], PROC_RUNNING

    ; Load page directory
    mov eax, [edi + PCB_PAGE_DIR]
    mov cr3, eax

    ; Restore all registers
    mov eax, [edi + PCB_EAX]
    mov ebx, [edi + PCB_EBX]
    mov ecx, [edi + PCB_ECX]
    mov edx, [edi + PCB_EDX]
    mov esi, [edi + PCB_ESI]
    mov ebp, [edi + PCB_EBP]
    mov esp, [edi + PCB_ESP]

    ; Push EIP and EFLAGS for iret-style return
    push dword [edi + PCB_EFLAGS]
    popfd

    ; Load EDI last (we were using it)
    push dword [edi + PCB_EIP]
    mov edi, [edi + PCB_EDI]

    ; Jump to process
    ret
