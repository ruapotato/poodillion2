# true - do nothing, successfully
# Part of PoodillionOS coreutils

const SYS_exit: int32 = 1

extern proc syscall1(num: int32, arg1: int32): int32

proc main() =
  discard syscall1(SYS_exit, 0)
