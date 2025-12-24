; process.asm - Process management and context switching for BrainhairOS
; Implements PCB, scheduler, and context switch

bits 32

; Process states
PROC_UNUSED   equ 0
PROC_READY    equ 1
PROC_RUNNING  equ 2
PROC_BLOCKED  equ 3
PROC_ZOMBIE   equ 4

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

PCB_SIZE      equ 128  ; Total size of PCB (with padding)

; Maximum number of processes
MAX_PROCS     equ 64

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
    mov dword [ready_count], 0
    mov dword [tick_count], 0

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
    ; Get current PCB
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .halt

    mov edi, eax

    ; Mark as ZOMBIE
    mov dword [edi + PCB_STATE], PROC_ZOMBIE

    ; Decrement ready count
    dec dword [ready_count]

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
; timer_tick - Called by timer interrupt to potentially reschedule
; ============================================================================
global timer_tick
timer_tick:
    ; Increment tick count
    inc dword [tick_count]

    ; Every 10 ticks, reschedule
    mov eax, [tick_count]
    and eax, 0x0F           ; Modulo 16
    jnz .no_switch

    ; Save all registers
    pusha

    ; Find next process
    call schedule

    ; If different from current, switch
    cmp eax, [current_pid]
    je .restore

    ; Context switch
    push eax
    call context_switch
    add esp, 4

.restore:
    popa

.no_switch:
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
