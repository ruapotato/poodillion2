# panicoverride.nim - Custom panic handler for PoodillionOS

{.push stack_trace: off, profiler: off.}

proc rawoutput(s: string) =
  # Output panic message to VGA
  let vga = cast[ptr UncheckedArray[uint16]](0xB8000)
  var i = 0
  for c in s:
    if i < 80 * 25:
      vga[i] = uint16(c.uint8) or (0x0C'u16 shl 8)  # Red on black
      inc i

proc panic(msg: string) {.exportc: "panic".} =
  rawoutput("KERNEL PANIC: ")
  rawoutput(msg)
  while true:
    {.emit: "asm volatile(\"cli; hlt\");".}

{.pop.}
