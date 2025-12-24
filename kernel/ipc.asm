; ipc.asm - Inter-Process Communication for BrainhairOS
; Implements synchronous message passing (send/recv/call/reply)

bits 32

; Message structure:
; - sender_pid (4 bytes)
; - receiver_pid (4 bytes)
; - data (24 bytes)
; Total: 32 bytes
MSG_SIZE        equ 32
MSG_SENDER      equ 0
MSG_RECEIVER    equ 4
MSG_DATA        equ 8

; Process waiting states (for PCB_WAITING field)
WAIT_NONE       equ 0       ; Not waiting
WAIT_ANY        equ -1      ; Waiting for message from any process

; Import from process.asm
extern process_table
extern current_pid
extern get_pcb
extern set_process_state
extern schedule
extern context_switch

; Process states (must match process.asm)
PROC_READY      equ 1
PROC_BLOCKED    equ 3

; PCB offsets (must match process.asm)
PCB_STATE       equ 4
PCB_WAITING     equ 68
PCB_MSG_BUF     equ 72
PCB_SIZE        equ 128
MAX_PROCS       equ 64

section .bss

; Message buffer pool (one message slot per process for simplicity)
align 4
global msg_buffers
msg_buffers:
    resb MSG_SIZE * MAX_PROCS

section .text

; ============================================================================
; ipc_send - Send a message to a process
; Input:
;   [esp+4] = destination PID
;   [esp+8] = pointer to message data (24 bytes)
; Returns: 0 on success, -1 on error
; ============================================================================
global ipc_send
ipc_send:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    ; Get destination PID
    mov ebx, [esp + 24]     ; dest_pid
    mov esi, [esp + 28]     ; msg_data pointer

    ; Validate destination PID
    cmp ebx, 0
    jl .send_error
    cmp ebx, MAX_PROCS
    jge .send_error

    ; Get destination PCB
    mov eax, ebx
    call get_pcb
    test eax, eax
    jz .send_error

    mov edi, eax            ; EDI = dest PCB

    ; Check if destination is waiting to receive from us (or any)
    mov eax, [edi + PCB_WAITING]
    cmp eax, WAIT_NONE
    je .send_block          ; Not waiting, we must block

    ; Check if waiting for us specifically or ANY
    cmp eax, WAIT_ANY
    je .send_deliver

    ; Waiting for specific sender - is it us?
    mov ecx, [current_pid]
    cmp eax, ecx
    jne .send_block         ; Not waiting for us

.send_deliver:
    ; Destination is ready to receive - copy message
    ; Get message buffer for destination
    mov eax, ebx            ; dest_pid
    imul eax, MSG_SIZE
    add eax, msg_buffers    ; EAX = dest msg buffer

    ; Set sender PID
    mov ecx, [current_pid]
    mov [eax + MSG_SENDER], ecx

    ; Set receiver PID
    mov [eax + MSG_RECEIVER], ebx

    ; Copy message data (24 bytes = 6 dwords)
    mov edi, eax
    add edi, MSG_DATA       ; Destination: msg buffer data area
    mov ecx, 6              ; 24 bytes / 4 = 6 dwords
    rep movsd

    ; Get dest PCB again (ESI was clobbered)
    mov eax, ebx
    call get_pcb
    mov edi, eax

    ; Wake up destination process
    mov dword [edi + PCB_WAITING], WAIT_NONE
    mov dword [edi + PCB_STATE], PROC_READY

    ; Return success
    xor eax, eax
    jmp .send_done

.send_block:
    ; TODO: Implement blocking send
    ; For now, return error (non-blocking)
    mov eax, -1
    jmp .send_done

.send_error:
    mov eax, -1

.send_done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; ipc_recv - Receive a message from a process
; Input:
;   [esp+4] = source PID (-1 for any)
;   [esp+8] = pointer to buffer for message data (24 bytes)
; Returns: sender PID on success, -1 on error
; ============================================================================
global ipc_recv
ipc_recv:
    push ebx
    push ecx
    push edx
    push esi
    push edi

    mov ebx, [esp + 24]     ; from_pid (-1 for any)
    mov edi, [esp + 28]     ; buffer pointer

    ; Get our PID
    mov ecx, [current_pid]

    ; Get our message buffer
    mov eax, ecx
    imul eax, MSG_SIZE
    add eax, msg_buffers
    mov esi, eax            ; ESI = our msg buffer

    ; Check if we have a pending message
    mov eax, [esi + MSG_RECEIVER]
    cmp eax, ecx
    jne .recv_block         ; No message for us

    ; Check if from correct sender (if specified)
    cmp ebx, WAIT_ANY
    je .recv_deliver        ; Accept from any

    mov eax, [esi + MSG_SENDER]
    cmp eax, ebx
    jne .recv_block         ; Not from who we want

.recv_deliver:
    ; Copy message data to user buffer
    add esi, MSG_DATA       ; Source: msg buffer data area
    mov ecx, 6              ; 24 bytes / 4 = 6 dwords
    rep movsd

    ; Get sender PID to return
    mov eax, ecx
    imul eax, MSG_SIZE
    add eax, msg_buffers
    mov eax, [eax + MSG_SENDER]

    ; Clear our message slot
    push eax
    mov eax, [current_pid]
    imul eax, MSG_SIZE
    add eax, msg_buffers
    mov dword [eax + MSG_RECEIVER], 0
    pop eax

    jmp .recv_done

.recv_block:
    ; Block until message arrives
    ; Get our PCB
    mov eax, [current_pid]
    call get_pcb
    test eax, eax
    jz .recv_error

    ; Set waiting state
    mov [eax + PCB_WAITING], ebx   ; Who we're waiting for
    mov dword [eax + PCB_STATE], PROC_BLOCKED

    ; Save buffer pointer in PCB for when message arrives
    mov ecx, [esp + 28]     ; buffer pointer
    mov [eax + PCB_MSG_BUF], ecx

    ; Yield to another process
    call schedule
    push eax
    call context_switch
    add esp, 4

    ; When we return, message should be delivered
    ; Get message from buffer
    mov eax, [current_pid]
    imul eax, MSG_SIZE
    add eax, msg_buffers
    mov eax, [eax + MSG_SENDER]
    jmp .recv_done

.recv_error:
    mov eax, -1

.recv_done:
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; ipc_call - RPC: send message and wait for reply
; Input:
;   [esp+4] = destination PID
;   [esp+8] = pointer to request message (24 bytes)
;   [esp+12] = pointer to reply buffer (24 bytes)
; Returns: 0 on success, -1 on error
; ============================================================================
global ipc_call
ipc_call:
    push ebx
    push edi

    mov eax, [esp + 12]     ; dest_pid
    mov ebx, [esp + 16]     ; request msg

    ; Send request
    push ebx
    push eax
    call ipc_send
    add esp, 8

    test eax, eax
    jnz .call_done          ; Send failed

    ; Wait for reply from same process
    mov edi, [esp + 20]     ; reply buffer
    mov eax, [esp + 12]     ; dest_pid (wait for reply from them)

    push edi
    push eax
    call ipc_recv
    add esp, 8

    ; Return recv result
.call_done:
    pop edi
    pop ebx
    ret

; ============================================================================
; ipc_reply - Reply to a calling process
; Input:
;   [esp+4] = destination PID (the caller)
;   [esp+8] = pointer to reply message (24 bytes)
; Returns: 0 on success, -1 on error
; ============================================================================
global ipc_reply
ipc_reply:
    ; Reply is just send
    jmp ipc_send
