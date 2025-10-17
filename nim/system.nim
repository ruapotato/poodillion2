# Minimal system module for PoodillionOS
# This replaces Nim's standard system module

type
  csize_t* = culong
  int* = int32
  uint* = uint32

# Memory functions (required by Nim)
proc nimCopy(dest, src: pointer, size: csize_t) {.compilerProc, inline.} =
  {.emit: "memcpy(`dest`, `src`, `size`);".}

proc nimZeroMem(p: pointer, size: csize_t) {.compilerProc, inline.} =
  {.emit: "memset(`p`, 0, `size`);".}

proc nimSetMem(p: pointer, val: csize_t, size: csize_t) {.compilerProc, inline.} =
  {.emit: "memset(`p`, `val`, `size`);".}

# Panic handler
proc rawoutput(s: cstring) =
  discard

proc panic(s: cstring) {.noreturn.} =
  rawoutput(s)
  while true:
    {.emit: "asm(\"hlt\");".}
