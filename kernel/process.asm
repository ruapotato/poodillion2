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

PCB_SIZE      equ 128  ; Total size of PCB (with padding)

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
    mov [edi + PCB_ESP], esp

    ; Save return address as EIP
    mov eax, [esp]
    mov [edi + PCB_EIP], eax

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
