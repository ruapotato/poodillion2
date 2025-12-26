; signal.asm - Unix signal handling for BrainhairOS
; Implements POSIX-like signals: kill(), signal(), sigprocmask()

bits 32

; ============================================================================
; Signal Numbers (POSIX standard)
; ============================================================================
SIGHUP      equ 1       ; Hangup
SIGINT      equ 2       ; Interrupt (Ctrl+C)
SIGQUIT     equ 3       ; Quit
SIGILL      equ 4       ; Illegal instruction
SIGTRAP     equ 5       ; Trace/breakpoint trap
SIGABRT     equ 6       ; Abort
SIGBUS      equ 7       ; Bus error
SIGFPE      equ 8       ; Floating point exception
SIGKILL     equ 9       ; Kill (cannot be caught)
SIGUSR1     equ 10      ; User-defined signal 1
SIGSEGV     equ 11      ; Segmentation fault
SIGUSR2     equ 12      ; User-defined signal 2
SIGPIPE     equ 13      ; Broken pipe
SIGALRM     equ 14      ; Alarm clock
SIGTERM     equ 15      ; Termination
SIGCHLD     equ 17      ; Child stopped or terminated
SIGCONT     equ 18      ; Continue if stopped
SIGSTOP     equ 19      ; Stop (cannot be caught)
SIGTSTP     equ 20      ; Terminal stop (Ctrl+Z)
SIGTTIN     equ 21      ; Background read from tty
SIGTTOU     equ 22      ; Background write to tty

MAX_SIGNALS equ 32      ; Maximum signal number

; Signal handler special values
SIG_DFL     equ 0       ; Default action
SIG_IGN     equ 1       ; Ignore signal
SIG_ERR     equ -1      ; Error return

; Default signal actions (encoded as bits)
SIG_ACTION_TERM     equ 0   ; Terminate process
SIG_ACTION_IGNORE   equ 1   ; Ignore signal
SIG_ACTION_STOP     equ 2   ; Stop process
SIG_ACTION_CONT     equ 3   ; Continue process
SIG_ACTION_CORE     equ 4   ; Core dump + terminate

; Process states needed (from process.asm)
PROC_UNUSED   equ 0
PROC_READY    equ 1
PROC_RUNNING  equ 2
PROC_BLOCKED  equ 3
PROC_ZOMBIE   equ 4
PROC_STOPPED  equ 5      ; New state for stopped processes

; PCB offsets for signals (new fields starting at offset 84)
PCB_PENDING_SIGNALS equ 84   ; uint32 - bitmask of pending signals
PCB_BLOCKED_SIGNALS equ 88   ; uint32 - bitmask of blocked signals
PCB_SIGNAL_HANDLERS equ 92   ; Offset to inline handler table (8 entries * 4 = 32 bytes)
; Handlers at 92, 96, 100, 104, 108, 112, 116, 120 for signals 1-8
; Higher signals use default actions only

PCB_SIZE     equ 128     ; Total PCB size (same as before, fits within padding)
MAX_PROCS    equ 16

; External references
extern current_pid
extern process_table
extern get_pcb
extern ready_count
extern schedule
extern context_switch

section .data

; Default actions for each signal (1-22)
; 0=term, 1=ignore, 2=stop, 3=cont, 4=core
default_actions:
    db 0    ; Signal 0 (invalid)
    db 0    ; SIGHUP (1) - terminate
    db 0    ; SIGINT (2) - terminate
    db 4    ; SIGQUIT (3) - core dump
    db 4    ; SIGILL (4) - core dump
    db 4    ; SIGTRAP (5) - core dump
    db 4    ; SIGABRT (6) - core dump
    db 4    ; SIGBUS (7) - core dump
    db 4    ; SIGFPE (8) - core dump
    db 0    ; SIGKILL (9) - terminate (cannot be caught)
    db 0    ; SIGUSR1 (10) - terminate
    db 4    ; SIGSEGV (11) - core dump
    db 0    ; SIGUSR2 (12) - terminate
    db 0    ; SIGPIPE (13) - terminate
    db 0    ; SIGALRM (14) - terminate
    db 0    ; SIGTERM (15) - terminate
    db 1    ; Signal 16 (unused) - ignore
    db 1    ; SIGCHLD (17) - ignore
    db 3    ; SIGCONT (18) - continue
    db 2    ; SIGSTOP (19) - stop (cannot be caught)
    db 2    ; SIGTSTP (20) - stop
    db 2    ; SIGTTIN (21) - stop
    db 2    ; SIGTTOU (22) - stop
    times 10 db 0   ; Signals 23-32 - terminate

section .text

; ============================================================================
; init_signals - Initialize signal subsystem
; Called during kernel startup
; ============================================================================
global init_signals
init_signals:
    push eax
    push ecx
    push edi

    ; Clear signal fields in all PCBs
    mov ecx, 0
.init_loop:
    cmp ecx, MAX_PROCS
    jge .init_done

    mov eax, ecx
    call get_pcb
    test eax, eax
    jz .init_next

    ; Clear pending and blocked signals
    mov dword [eax + PCB_PENDING_SIGNALS], 0
    mov dword [eax + PCB_BLOCKED_SIGNALS], 0

    ; Set all handlers to SIG_DFL (0)
    mov edi, eax
    add edi, PCB_SIGNAL_HANDLERS
    push ecx
    mov ecx, 8  ; 8 handler slots
    xor eax, eax
.clear_handlers:
    mov [edi], eax
    add edi, 4
    loop .clear_handlers
    pop ecx

.init_next:
    inc ecx
    jmp .init_loop

.init_done:
    pop edi
    pop ecx
    pop eax
    ret

; ============================================================================
; kill - Send a signal to a process
; Input:
;   [esp+4] = pid (target process)
;   [esp+8] = sig (signal number)
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global kill
global sys_kill
kill:
sys_kill:
    push ebx
    push ecx
    push edi

    mov eax, [esp + 16]     ; pid
    mov ebx, [esp + 20]     ; signal

    ; Validate signal number (1-31)
    test ebx, ebx
    jz .success             ; Signal 0 = just check if process exists
    cmp ebx, MAX_SIGNALS
    jge .error

    ; Special case: pid == 0 means current process
    test eax, eax
    jnz .have_pid
    mov eax, [current_pid]

.have_pid:
    ; Get target PCB
    call get_pcb
    test eax, eax
    jz .error

    mov edi, eax

    ; Check if process is valid (not unused/zombie for most signals)
    mov ecx, [edi]              ; PCB_STATE is at offset 4, but we need PCB_PID check
    mov ecx, [edi + 4]          ; Get state
    cmp ecx, PROC_UNUSED
    je .error
    cmp ecx, PROC_ZOMBIE
    je .error

    ; SIGKILL and SIGSTOP cannot be blocked or caught
    cmp ebx, SIGKILL
    je .deliver_signal
    cmp ebx, SIGSTOP
    je .deliver_signal

    ; Check if signal is blocked
    mov ecx, [edi + PCB_BLOCKED_SIGNALS]
    mov eax, 1
    push ecx
    mov ecx, ebx
    shl eax, cl                 ; Create signal mask
    pop ecx
    test ecx, eax
    jnz .success                ; Signal blocked, but that's not an error

.deliver_signal:
    ; Set pending bit
    mov eax, 1
    mov ecx, ebx
    shl eax, cl
    or [edi + PCB_PENDING_SIGNALS], eax

    ; If process is stopped and signal is SIGCONT, wake it
    cmp ebx, SIGCONT
    jne .check_blocked

    mov ecx, [edi + 4]          ; Get state
    cmp ecx, PROC_STOPPED
    jne .success

    ; Wake stopped process
    mov dword [edi + 4], PROC_READY
    inc dword [ready_count]
    jmp .success

.check_blocked:
    ; If process is blocked, and this is SIGKILL, terminate it
    cmp ebx, SIGKILL
    jne .success

    mov ecx, [edi + 4]
    cmp ecx, PROC_BLOCKED
    jne .success

    ; Process will be terminated when it's scheduled next
    ; Wake it up so it can be terminated
    mov dword [edi + 4], PROC_READY
    inc dword [ready_count]

.success:
    xor eax, eax
    pop edi
    pop ecx
    pop ebx
    ret

.error:
    mov eax, -1
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; signal - Set signal handler
; Input:
;   [esp+4] = sig (signal number)
;   [esp+8] = handler (SIG_DFL, SIG_IGN, or function pointer)
; Returns: EAX = previous handler, or SIG_ERR on error
; ============================================================================
global signal
global sys_signal
signal:
sys_signal:
    push ebx
    push ecx
    push edi

    mov ebx, [esp + 16]     ; signal number
    mov ecx, [esp + 20]     ; new handler

    ; Validate signal (1-8 for custom handlers)
    test ebx, ebx
    jz .sig_error
    cmp ebx, 8
    jg .sig_error

    ; SIGKILL (9) and SIGSTOP (19) cannot be caught
    cmp ebx, SIGKILL
    je .sig_error
    cmp ebx, SIGSTOP
    je .sig_error

    ; Get current process PCB
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .sig_error

    mov edi, eax

    ; Calculate handler offset: PCB_SIGNAL_HANDLERS + (sig - 1) * 4
    mov eax, ebx
    dec eax
    shl eax, 2
    add eax, PCB_SIGNAL_HANDLERS
    add eax, edi

    ; Get old handler
    push ecx
    mov ecx, [eax]
    push ecx            ; Save old handler

    ; Set new handler
    pop ecx             ; Old handler
    pop edx             ; New handler (was pushed as ecx)
    mov [eax], edx

    ; Return old handler
    mov eax, ecx

    pop edi
    pop ecx
    pop ebx
    ret

.sig_error:
    mov eax, SIG_ERR
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; sigprocmask - Block/unblock signals
; Input:
;   [esp+4] = how (0=SIG_BLOCK, 1=SIG_UNBLOCK, 2=SIG_SETMASK)
;   [esp+8] = set (signal mask to apply)
;   [esp+12] = oldset (pointer to store old mask, or NULL)
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
SIG_BLOCK   equ 0
SIG_UNBLOCK equ 1
SIG_SETMASK equ 2

global sigprocmask
global sys_sigprocmask
sigprocmask:
sys_sigprocmask:
    push ebx
    push ecx
    push edi

    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .mask_error

    mov edi, eax

    mov eax, [esp + 16]     ; how
    mov ebx, [esp + 20]     ; set
    mov ecx, [esp + 24]     ; oldset

    ; Store old mask if requested
    test ecx, ecx
    jz .no_oldset
    mov edx, [edi + PCB_BLOCKED_SIGNALS]
    mov [ecx], edx

.no_oldset:
    ; Can't block SIGKILL or SIGSTOP
    and ebx, ~((1 << SIGKILL) | (1 << SIGSTOP))

    cmp eax, SIG_BLOCK
    je .do_block
    cmp eax, SIG_UNBLOCK
    je .do_unblock
    cmp eax, SIG_SETMASK
    je .do_setmask
    jmp .mask_error

.do_block:
    or [edi + PCB_BLOCKED_SIGNALS], ebx
    jmp .mask_success

.do_unblock:
    not ebx
    and [edi + PCB_BLOCKED_SIGNALS], ebx
    jmp .mask_success

.do_setmask:
    mov [edi + PCB_BLOCKED_SIGNALS], ebx

.mask_success:
    xor eax, eax
    pop edi
    pop ecx
    pop ebx
    ret

.mask_error:
    mov eax, -1
    pop edi
    pop ecx
    pop ebx
    ret

; ============================================================================
; check_signals - Check and deliver pending signals for current process
; Called during context switch / return to user mode
; Returns: EAX = 1 if process should terminate, 0 otherwise
; ============================================================================
global check_signals
check_signals:
    push ebx
    push ecx
    push edx
    push edi
    push esi

    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .no_signals

    mov edi, eax

    ; Get pending signals not blocked
    mov eax, [edi + PCB_PENDING_SIGNALS]
    mov ebx, [edi + PCB_BLOCKED_SIGNALS]
    not ebx
    and eax, ebx                ; Unblocked pending signals
    test eax, eax
    jz .no_signals

    ; Find first pending signal (bit scan)
    mov ecx, 1
.find_signal:
    cmp ecx, MAX_SIGNALS
    jge .no_signals

    mov edx, 1
    push ecx
    shl edx, cl
    pop ecx
    test eax, edx
    jnz .found_signal
    inc ecx
    jmp .find_signal

.found_signal:
    ; ECX = signal number
    ; Clear pending bit
    not edx
    and [edi + PCB_PENDING_SIGNALS], edx

    ; SIGKILL - always terminate
    cmp ecx, SIGKILL
    je .do_terminate

    ; SIGSTOP - always stop
    cmp ecx, SIGSTOP
    je .do_stop

    ; Check for custom handler (signals 1-8)
    cmp ecx, 8
    jg .check_default

    ; Get handler
    mov eax, ecx
    dec eax
    shl eax, 2
    add eax, PCB_SIGNAL_HANDLERS
    add eax, edi
    mov esi, [eax]          ; ESI = handler

    ; SIG_IGN?
    cmp esi, SIG_IGN
    je .signal_handled

    ; SIG_DFL?
    cmp esi, SIG_DFL
    je .check_default

    ; Custom handler - call it
    ; TODO: Proper signal trampoline for user space
    ; For now, just call the handler directly (kernel mode only)
    push ecx                ; Signal number as argument
    call esi
    add esp, 4
    jmp .signal_handled

.check_default:
    ; Get default action
    movzx eax, byte [default_actions + ecx]

    cmp eax, SIG_ACTION_TERM
    je .do_terminate
    cmp eax, SIG_ACTION_CORE
    je .do_terminate        ; No core dump for now
    cmp eax, SIG_ACTION_STOP
    je .do_stop
    cmp eax, SIG_ACTION_CONT
    je .do_continue
    ; SIG_ACTION_IGNORE - fall through

.signal_handled:
    ; Check for more signals
    mov eax, [edi + PCB_PENDING_SIGNALS]
    mov ebx, [edi + PCB_BLOCKED_SIGNALS]
    not ebx
    and eax, ebx
    test eax, eax
    jnz .find_signal

.no_signals:
    xor eax, eax            ; Return 0 - don't terminate
    pop esi
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

.do_terminate:
    ; Terminate the process
    mov eax, 1              ; Return 1 - terminate
    pop esi
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

.do_stop:
    ; Stop the process
    mov dword [edi + 4], PROC_STOPPED
    dec dword [ready_count]

    ; Schedule another process
    call schedule
    push eax
    call context_switch
    add esp, 4

    ; When we return, we've been continued
    jmp .signal_handled

.do_continue:
    ; Already running, nothing to do
    jmp .signal_handled

; ============================================================================
; raise - Send signal to self
; Input: [esp+4] = signal number
; Returns: EAX = 0 on success
; ============================================================================
global raise
global sys_raise
raise:
sys_raise:
    push dword [esp + 4]        ; Signal
    push dword [current_pid]    ; Self
    call kill
    add esp, 8
    ret

; ============================================================================
; sigpending - Get pending signals
; Input: [esp+4] = set (pointer to store pending mask)
; Returns: EAX = 0 on success
; ============================================================================
global sigpending
sigpending:
    push edi

    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .pending_error

    mov edi, [esp + 8]      ; set pointer
    test edi, edi
    jz .pending_error

    mov eax, [eax + PCB_PENDING_SIGNALS]
    mov [edi], eax

    xor eax, eax
    pop edi
    ret

.pending_error:
    mov eax, -1
    pop edi
    ret

; ============================================================================
; Export signal constants for other modules
; ============================================================================
global sig_int
global sig_term
global sig_kill
global sig_stop
global sig_cont
global sig_chld

sig_int:  dd SIGINT
sig_term: dd SIGTERM
sig_kill: dd SIGKILL
sig_stop: dd SIGSTOP
sig_cont: dd SIGCONT
sig_chld: dd SIGCHLD
