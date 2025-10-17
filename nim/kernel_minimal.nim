# kernel_minimal.nim - Ultra-minimal PoodillionOS Kernel
# Zero stdlib, pure bare metal

{.push stack_trace: off, profiler: off, checks: off.}

# Custom types (no stdlib!)
type
  csize_t = culong
  cchar = char

# Port I/O - inline assembly
proc outb(port: uint16, val: uint8) {.inline.} =
  {.emit: "asm volatile(\"outb %0, %1\" : : \"a\"(`val`), \"Nd\"(`port`));".}

proc inb(port: uint16): uint8 {.inline.} =
  var ret: uint8
  {.emit: "asm volatile(\"inb %1, %0\" : \"=a\"(`ret`) : \"Nd\"(`port`));".}
  ret

proc hlt() {.inline.} =
  {.emit: "asm volatile(\"hlt\");".}

# VGA text mode
const
  VGA_WIDTH = 80
  VGA_HEIGHT = 25
  VGA_BUFFER = 0xB8000'u32

var vgaBuffer = cast[ptr UncheckedArray[uint16]](VGA_BUFFER)
var row = 0
var col = 0

proc vgaEntry(c: char, color: uint8): uint16 {.inline.} =
  uint16(c.uint8) or (uint16(color) shl 8)

proc vgaClear() =
  for i in 0 ..< (VGA_WIDTH * VGA_HEIGHT):
    vgaBuffer[i] = vgaEntry(' ', 0x0F)
  row = 0
  col = 0

proc vgaScroll() =
  # Move lines up
  for y in 0 ..< (VGA_HEIGHT - 1):
    for x in 0 ..< VGA_WIDTH:
      vgaBuffer[y * VGA_WIDTH + x] = vgaBuffer[(y + 1) * VGA_WIDTH + x]
  # Clear bottom
  for x in 0 ..< VGA_WIDTH:
    vgaBuffer[(VGA_HEIGHT - 1) * VGA_WIDTH + x] = vgaEntry(' ', 0x0F)

proc vgaPutChar(c: char, color: uint8 = 0x0F) =
  if c == '\n':
    col = 0
    inc row
    if row >= VGA_HEIGHT:
      row = VGA_HEIGHT - 1
      vgaScroll()
    return

  vgaBuffer[row * VGA_WIDTH + col] = vgaEntry(c, color)
  inc col
  if col >= VGA_WIDTH:
    col = 0
    inc row
    if row >= VGA_HEIGHT:
      row = VGA_HEIGHT - 1
      vgaScroll()

proc vgaPrint(s: cstring, color: uint8 = 0x0F) =
  var i = 0
  while s[i] != '\0':
    vgaPutChar(s[i], color)
    inc i

# Keyboard
const
  KBD_DATA = 0x60'u16
  KBD_STATUS = 0x64'u16

var shiftPressed = false

# Scancode to ASCII table (simplified)
const scancodes = [
  '\0', '\0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b',
  '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',
  '\0', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`',
  '\0', '\\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', '\0',
  '*', '\0', ' '
]

const scancodes_shift = [
  '\0', '\0', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '\b',
  '\t', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '\n',
  '\0', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~',
  '\0', '|', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', '\0',
  '*', '\0', ' '
]

proc kbdAvailable(): bool =
  (inb(KBD_STATUS) and 1) != 0

proc kbdGetChar(): char =
  while not kbdAvailable():
    discard

  let sc = inb(KBD_DATA)

  # Key release
  if (sc and 0x80) != 0:
    let code = sc and 0x7F
    if code == 0x2A or code == 0x36:  # Shift
      shiftPressed = false
    return '\0'

  # Key press
  if sc == 0x2A or sc == 0x36:  # Shift
    shiftPressed = true
    return '\0'

  if sc < scancodes.len:
    if shiftPressed:
      return scancodes_shift[sc]
    else:
      return scancodes[sc]

  return '\0'

# String compare (no stdlib!)
proc streq(a, b: cstring): bool =
  var i = 0
  while true:
    if a[i] != b[i]:
      return false
    if a[i] == '\0':
      return true
    inc i

# Command buffer
var cmdBuf: array[256, char]
var cmdLen = 0

proc execCommand() =
  if cmdLen == 0:
    return

  cmdBuf[cmdLen] = '\0'
  let cmd = cast[cstring](addr cmdBuf[0])

  if streq(cmd, "help"):
    vgaPrint("PoodillionOS - Nim Kernel!\n", 0x0B)
    vgaPrint("Commands: help, clear, about, halt\n", 0x0F)
  elif streq(cmd, "clear"):
    vgaClear()
  elif streq(cmd, "about"):
    vgaPrint("PoodillionOS v0.2 (Nim Edition)\n", 0x0B)
    vgaPrint("100% Nim kernel - bare metal!\n", 0x0F)
  elif streq(cmd, "halt"):
    vgaPrint("System halted.\n", 0x0E)
    while true:
      hlt()
  else:
    vgaPrint("Unknown command: ", 0x0C)
    vgaPrint(cmd, 0x0C)
    vgaPrint("\n", 0x0C)

proc shell() =
  vgaPrint("root@poodillion# ", 0x0A)

  while true:
    let c = kbdGetChar()
    if c == '\0':
      continue

    if c == '\n':
      vgaPutChar('\n')
      execCommand()
      cmdLen = 0
      vgaPrint("root@poodillion# ", 0x0A)
    elif c == '\b':
      if cmdLen > 0:
        dec cmdLen
        # Backspace: move back, print space, move back
        if col > 0:
          dec col
          vgaBuffer[row * VGA_WIDTH + col] = vgaEntry(' ', 0x0F)
    else:
      if cmdLen < cmdBuf.len - 1:
        cmdBuf[cmdLen] = c
        inc cmdLen
        vgaPutChar(c)

# Kernel entry point
proc kernel_main() {.exportc, cdecl.} =
  vgaClear()

  vgaPrint("PoodillionOS v0.2.0 - Nim Edition!\n", 0x0A)
  vgaPrint("===================================\n\n", 0x0A)

  vgaPrint("Pure Nim kernel - bare metal x86\n", 0x0F)
  vgaPrint("Type 'help' for commands\n\n", 0x07)

  shell()

{.pop.}
