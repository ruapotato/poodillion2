# pthread Implementation for BrainhairOS

## Overview

This document describes the pthread-compatible threading implementation for BrainhairOS. The implementation follows a **1:1 threading model** where each user-space pthread maps directly to one kernel thread.

## Architecture

### Threading Model: 1:1 (Kernel-Level Threads)

- Each `pthread_t` is backed by a kernel thread with its own PCB entry
- Threads share the same address space (page directory) as the parent process
- Each thread has an independent 4KB kernel stack
- Thread scheduling is handled by the kernel scheduler alongside processes

### Key Components

#### 1. Kernel Thread Support (`kernel/process.asm`)

**PCB Fields (Process Control Block):**
- `PCB_IS_THREAD` - Flag indicating if this PCB is a thread (1) or process (0)
- `PCB_MAIN_PROC` - PID of the main process (for threads)
- `PCB_THREAD_ID` - Thread ID within the process (0 for main, 1+ for threads)
- `PCB_NEXT_TID` - Next thread ID to assign (main process only)
- `PCB_THREAD_EXIT_STATUS` - Exit status when thread terminates
- `PCB_THREAD_JOINED` - Flag indicating if thread has been joined
- `PCB_THREAD_JOINER` - PID of thread waiting to join (0 = none)
- `PCB_THREAD_DETACHED` - Flag for detached threads (auto-cleanup)

**Kernel Functions:**
- `thread_create(entry, arg)` - Create new thread with entry point and argument
- `thread_exit(code)` - Exit current thread with exit code
- `thread_yield()` - Yield CPU to other threads/processes
- `get_thread_id()` - Get current thread's ID (0 for main process)
- `is_thread()` - Check if current context is a thread
- `thread_join(tid, status_ptr)` - Wait for thread to exit and get status
- `thread_detach(tid)` - Mark thread as detached (auto-cleanup on exit)

#### 2. Syscall Interface (`kernel/isr.asm`)

**Thread Syscalls (200-206):**
- `200` - `SYS_thread_create` - Create new thread
- `201` - `SYS_thread_exit` - Exit current thread
- `202` - `SYS_thread_yield` - Yield to scheduler
- `203` - `SYS_get_thread_id` - Get thread ID
- `204` - `SYS_is_thread` - Check if thread
- `205` - `SYS_thread_join` - Join thread (NEW)
- `206` - `SYS_thread_detach` - Detach thread (NEW)

#### 3. Low-Level Thread API (`lib/syscalls.bh`)

Provides direct syscall wrappers:
- `thread_create(entry, arg)` -> thread PID
- `thread_exit(code)` -> void
- `thread_yield()` -> void
- `thread_self()` / `get_thread_id()` -> thread ID
- `is_thread()` -> bool
- `thread_join(tid, status_ptr)` -> 0 on success, -1 on error
- `thread_detach(tid)` -> 0 on success, -1 on error

#### 4. POSIX pthread API (`lib/pthread.bh`)

POSIX-compatible pthread interface:

**Types:**
- `pthread_t` - Thread identifier (maps to kernel thread PID)
- `pthread_attr_t` - Thread attributes

**Functions:**
- `pthread_create(thread, attr, start_routine, arg)` - Create thread
- `pthread_join(thread, retval)` - Wait for thread termination
- `pthread_exit(retval)` - Terminate calling thread
- `pthread_self()` - Get current thread ID
- `pthread_equal(t1, t2)` - Compare thread IDs
- `pthread_detach(thread)` - Detach thread
- `pthread_yield()` - Yield CPU
- `pthread_attr_init(attr)` - Initialize thread attributes
- `pthread_attr_setdetachstate(attr, state)` - Set detach state

## Thread Lifecycle

### 1. Thread Creation

```
pthread_create()
  └─> thread_create(entry, arg)  [syscall 200]
      └─> kernel: thread_create()
          ├─> Allocate new PCB slot
          ├─> Set PCB_IS_THREAD = 1
          ├─> Share page directory with parent
          ├─> Allocate 4KB kernel stack
          ├─> Set up initial stack frame (entry point + arg)
          ├─> Set state to PROC_READY
          └─> Return thread PID
```

### 2. Thread Execution

- Thread starts at specified entry point with argument in register
- Runs in same address space as parent process
- Can be scheduled like any other process
- When entry function returns, `thread_exit_trampoline` is called automatically

### 3. Thread Termination

**Normal Exit:**
```
pthread_exit(retval)
  └─> thread_exit(code)  [syscall 201]
      └─> kernel: thread_exit()
          ├─> Save exit status in PCB_THREAD_EXIT_STATUS
          ├─> Check if detached:
          │   ├─> YES: Clean up PCB immediately
          │   └─> NO: Check if joiner exists:
          │       ├─> YES: Wake joiner, mark PROC_READY
          │       └─> NO: Become ZOMBIE, wait for join
          └─> Schedule next thread/process
```

**Detached Thread Exit:**
- Thread PCB is immediately freed
- No zombie state needed
- Cannot be joined

### 4. Thread Join

```
pthread_join(thread, retval)
  └─> thread_join(tid, status_ptr)  [syscall 205]
      └─> kernel: thread_join()
          ├─> Validate thread (is thread, not detached, not already joined)
          ├─> Check thread state:
          │   ├─> ZOMBIE: Get exit status immediately
          │   └─> RUNNING/READY:
          │       ├─> Set ourselves as joiner in PCB_THREAD_JOINER
          │       ├─> Block (PROC_BLOCKED)
          │       └─> Wait for thread to exit (woken by thread_exit)
          ├─> Retrieve exit status from PCB_THREAD_EXIT_STATUS
          ├─> Mark PCB_THREAD_JOINED = 1
          ├─> Clean up thread PCB
          └─> Return exit status
```

### 5. Thread Detach

```
pthread_detach(thread)
  └─> thread_detach(tid)  [syscall 206]
      └─> kernel: thread_detach()
          ├─> Validate thread (is thread, not already joined)
          ├─> Set PCB_THREAD_DETACHED = 1
          └─> Return success
```

## Memory Management

### Address Space Sharing

- All threads share the same page directory (`PCB_PAGE_DIR`)
- Threads can access all parent process memory
- Global variables are shared
- Stack is thread-local (each thread has independent kernel stack)

### Stack Layout

Each thread gets a 4KB kernel stack located at:
```
kernel_stacks + (slot_index * 4096)
```

Initial stack setup for new thread:
```
[stack_top - 8]  thread_exit_trampoline  <- ESP starts here
[stack_top - 4]  user argument
```

When thread function is called:
- Return address points to `thread_exit_trampoline`
- Argument is passed on stack (or in register, depending on calling convention)
- When function returns, exit code in EAX is automatically passed to `thread_exit`

## Synchronization

Thread join implements blocking synchronization:

1. Joiner calls `pthread_join(thread, &status)`
2. If thread is still running:
   - Joiner's PID is stored in `PCB_THREAD_JOINER`
   - Joiner's state set to `PROC_BLOCKED`
   - Joiner descheduled (removed from ready queue)
3. When thread exits:
   - Check `PCB_THREAD_JOINER`
   - If joiner exists, set joiner state to `PROC_READY`
   - Joiner will be rescheduled and resume execution
4. Joiner retrieves exit status and cleans up thread PCB

## Error Handling

`pthread_join()` returns error (-1) if:
- Invalid thread ID
- Target is not a thread
- Thread already joined
- Thread is detached
- Thread doesn't exist (PROC_UNUSED)

`pthread_detach()` returns error (-1) if:
- Invalid thread ID
- Target is not a thread
- Thread already joined

## Limitations

1. **No user-space stacks**: Threads currently use kernel stacks only. User-space stack allocation not implemented.

2. **Simple entry wrapper**: Thread functions must match signature `proc(arg: int32): int32`. More complex wrappers would require heap allocation.

3. **No attributes support**: `pthread_attr_t` only supports detach state. Stack size, scheduling policy, etc. not implemented.

4. **No thread cancellation**: `pthread_cancel()` not implemented.

5. **No thread-local storage (TLS)**: While PCB has `PCB_TLS_BASE`, full TLS support not implemented.

6. **Fixed thread limit**: Maximum 16 threads per system (shared with processes due to MAX_PROCS=16).

## Testing

Test program: `userland/pthread_test.bh`

Build and run:
```bash
make pthread-test
./bin/pthread_test
```

Tests include:
1. Basic thread creation and join
2. Multiple concurrent threads
3. Detached threads
4. Thread identity (pthread_self, pthread_equal)
5. Join without return value

## Future Enhancements

1. **User-space stacks**: Allocate separate user stacks for threads
2. **Thread cancellation**: Implement `pthread_cancel()`
3. **Full TLS support**: Thread-local storage with `__thread` variables
4. **More attributes**: Stack size, scheduling policy, priority
5. **Thread pools**: Efficient thread reuse
6. **Condition variables**: `pthread_cond_wait()` and `pthread_cond_signal()`
7. **Barriers**: `pthread_barrier_wait()`
8. **Read-write locks**: `pthread_rwlock_*`
9. **Once initialization**: `pthread_once()`
10. **Increase MAX_PROCS**: Support more concurrent threads

## API Reference

### pthread_create
```c
int pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                   void *(*start_routine)(void*), void *arg);
```
Creates a new thread executing `start_routine` with argument `arg`.

### pthread_join
```c
int pthread_join(pthread_t thread, void **retval);
```
Waits for thread to terminate and retrieves its exit status.

### pthread_exit
```c
void pthread_exit(void *retval);
```
Terminates the calling thread with exit value `retval`.

### pthread_detach
```c
int pthread_detach(pthread_t thread);
```
Marks thread as detached. Resources freed automatically on exit.

### pthread_self
```c
pthread_t pthread_self(void);
```
Returns the thread ID of the calling thread.

### pthread_equal
```c
int pthread_equal(pthread_t t1, pthread_t t2);
```
Compares two thread IDs for equality.

## Compatibility

This implementation aims for POSIX pthread compatibility but has some differences:

**Compatible:**
- Thread creation, joining, detaching
- Thread self-identification
- Detach state attributes
- Return value passing

**Not Compatible:**
- Limited attribute support
- No cancellation
- No TLS
- Different thread ID type (int32 vs opaque handle)
- No cleanup handlers
- No scheduling attributes

## License

Part of BrainhairOS - See project LICENSE file.
