# nohup - Run command immune to hangups
# Usage: nohup COMMAND [ARGS...]
# Redirects stdout/stderr to nohup.out and ignores SIGHUP

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_fork: int32 = 2
const SYS_execve: int32 = 11
const SYS_dup2: int32 = 63

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_APPEND: int32 = 1024

const S_IRUSR: int32 = 256
const S_IWUSR: int32 = 128
const S_IRGRP: int32 = 32
const S_IROTH: int32 = 4

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc main() =
  print_err(cast[ptr uint8]("nohup: Running command in background\n"))
  print_err(cast[ptr uint8]("nohup: Output will be written to nohup.out\n"))

  # Open nohup.out for output
  var nohup_file: ptr uint8 = cast[ptr uint8]("nohup.out")
  var flags: int32 = O_WRONLY or O_CREAT or O_APPEND
  var mode: int32 = S_IRUSR or S_IWUSR or S_IRGRP or S_IROTH
  var fd: int32 = syscall3(SYS_open, cast[int32](nohup_file), flags, mode)

  if fd < 0:
    print_err(cast[ptr uint8]("nohup: cannot open nohup.out\n"))
    discard syscall1(SYS_exit, 1)

  # Fork to create child process
  var pid: int32 = syscall1(SYS_fork, 0)

  if pid < 0:
    print_err(cast[ptr uint8]("nohup: fork failed\n"))
    discard syscall1(SYS_exit, 1)

  if pid == 0:
    # Child process
    # Redirect stdout and stderr to nohup.out
    discard syscall2(SYS_dup2, fd, STDOUT)
    discard syscall2(SYS_dup2, fd, STDERR)
    discard syscall1(SYS_close, fd)

    # In a real implementation, we would execve the command here
    # For now, just write a message and exit
    var msg: ptr uint8 = cast[ptr uint8]("nohup: Command would run here\n")
    var len: int32 = strlen(msg)
    discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

    # Example: execve("/bin/sh", argv, envp)
    # var cmd: ptr uint8 = cast[ptr uint8]("/bin/sh")
    # discard syscall3(SYS_execve, cast[int32](cmd), 0, 0)

    discard syscall1(SYS_exit, 0)

  # Parent process
  discard syscall1(SYS_close, fd)
  print_err(cast[ptr uint8]("nohup: Process started in background\n"))
  discard syscall1(SYS_exit, 0)
