{.push stack_trace: off, profiler: off.}
{.pragma: exportc, exportc, dynlib, cdecl.}

# Disable standard library
proc alloc(size: Natural): pointer {.exportc: "alloc", used.} =
  # Simple bump allocator - just for boot
  {.emit: "static char heap[1024*1024]; static size_t heap_pos = 0;".}
  {.emit: "if (heap_pos + `size` > sizeof(heap)) return 0;".}
  {.emit: "void* p = &heap[heap_pos];".}
  {.emit: "heap_pos += `size`;".}
  {.emit: "return p;".}

proc dealloc(p: pointer) {.exportc: "dealloc", used.} =
  discard  # No-op for now

# kernel.nim - PoodillionOS Kernel in Nim!
# Compiles to freestanding C for bare metal

const
  VGA_WIDTH = 80
  VGA_HEIGHT = 25
  VGA_MEMORY = cast[ptr UncheckedArray[uint16]](0xB8000)

type
  VgaColor* = enum
    Black = 0
    Blue = 1
    Green = 2
    Cyan = 3
    Red = 4
    Magenta = 5
    Brown = 6
    LightGrey = 7
    DarkGrey = 8
    LightBlue = 9
    LightGreen = 10
    LightCyan = 11
    LightRed = 12
    LightMagenta = 13
    Yellow = 14
    White = 15

  Terminal = object
    row: int
    col: int
    color: uint8

var terminal: Terminal

proc vgaEntry(c: char, color: uint8): uint16 {.inline.} =
  uint16(c.uint8) or (uint16(color) shl 8)

proc vgaColor(fg, bg: VgaColor): uint8 {.inline.} =
  fg.uint8 or (bg.uint8 shl 4)

proc terminalClear*() =
  terminal.row = 0
  terminal.col = 0
  terminal.color = vgaColor(LightGreen, Black)

  for i in 0 ..< (VGA_WIDTH * VGA_HEIGHT):
    VGA_MEMORY[i] = vgaEntry(' ', terminal.color)

proc terminalScroll() =
  # Move all lines up
  for y in 0 ..< (VGA_HEIGHT - 1):
    for x in 0 ..< VGA_WIDTH:
      VGA_MEMORY[y * VGA_WIDTH + x] = VGA_MEMORY[(y + 1) * VGA_WIDTH + x]

  # Clear bottom line
  for x in 0 ..< VGA_WIDTH:
    VGA_MEMORY[(VGA_HEIGHT - 1) * VGA_WIDTH + x] = vgaEntry(' ', terminal.color)

proc terminalPutChar*(c: char) =
  if c == '\n':
    terminal.col = 0
    inc terminal.row
    if terminal.row >= VGA_HEIGHT:
      terminal.row = VGA_HEIGHT - 1
      terminalScroll()
    return

  if c == '\b':
    if terminal.col > 0:
      dec terminal.col
      VGA_MEMORY[terminal.row * VGA_WIDTH + terminal.col] = vgaEntry(' ', terminal.color)
    return

  VGA_MEMORY[terminal.row * VGA_WIDTH + terminal.col] = vgaEntry(c, terminal.color)
  inc terminal.col

  if terminal.col >= VGA_WIDTH:
    terminal.col = 0
    inc terminal.row
    if terminal.row >= VGA_HEIGHT:
      terminal.row = VGA_HEIGHT - 1
      terminalScroll()

proc terminalWrite*(s: string) =
  for c in s:
    terminalPutChar(c)

proc terminalSetColor*(fg, bg: VgaColor) =
  terminal.color = vgaColor(fg, bg)

# Keyboard driver
const
  KBD_DATA_PORT = 0x60'u16
  KBD_STATUS_PORT = 0x64'u16

proc inb(port: uint16): uint8 {.importc: "inb_nim", header: "kernel_support.h".}
proc outb(port: uint16, val: uint8) {.importc: "outb_nim", header: "kernel_support.h".}
proc hlt() {.importc: "hlt_nim", header: "kernel_support.h".}

var
  shiftPressed = false
  ctrlPressed = false

const scancodeToAscii = [
  '\0', '\e', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b',
  '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',
  '\0', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`',
  '\0', '\\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', '\0',
  '*', '\0', ' '
]

const scancodeToAsciiShift = [
  '\0', '\e', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '\b',
  '\t', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '\n',
  '\0', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~',
  '\0', '|', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', '\0',
  '*', '\0', ' '
]

proc keyboardAvailable*(): bool =
  (inb(KBD_STATUS_PORT) and 0x01) != 0

proc keyboardGetChar*(): char =
  while not keyboardAvailable():
    discard  # Wait for key

  let scancode = inb(KBD_DATA_PORT)

  # Key release (high bit set)
  if (scancode and 0x80) != 0:
    let sc = scancode and 0x7F
    if sc == 0x2A or sc == 0x36:  # Shift
      shiftPressed = false
    elif sc == 0x1D:  # Ctrl
      ctrlPressed = false
    return '\0'

  # Key press
  if scancode == 0x2A or scancode == 0x36:  # Shift
    shiftPressed = true
    return '\0'
  elif scancode == 0x1D:  # Ctrl
    ctrlPressed = true
    return '\0'

  # Convert to ASCII
  if scancode < scancodeToAscii.len:
    if shiftPressed:
      return scancodeToAsciiShift[scancode]
    else:
      return scancodeToAscii[scancode]

  return '\0'

# String utilities
proc strcmp(a, b: string): bool =
  if a.len != b.len:
    return false
  for i in 0 ..< a.len:
    if a[i] != b[i]:
      return false
  return true

proc startsWith(s, prefix: string): bool =
  if s.len < prefix.len:
    return false
  for i in 0 ..< prefix.len:
    if s[i] != prefix[i]:
      return false
  return true

# Command handling
proc handleCommand(cmd: string) =
  if cmd.len == 0:
    return

  if strcmp(cmd, "help"):
    terminalWrite("PoodillionOS Commands:\n")
    terminalWrite("  help    - Show this help\n")
    terminalWrite("  clear   - Clear screen\n")
    terminalWrite("  about   - About PoodillionOS\n")
    terminalWrite("  halt    - Halt the system\n")

  elif strcmp(cmd, "clear"):
    terminalClear()

  elif strcmp(cmd, "about"):
    terminalSetColor(LightCyan, Black)
    terminalWrite("PoodillionOS v0.2.0 - Nim Edition!\n")
    terminalSetColor(White, Black)
    terminalWrite("A Unix-like OS written in Nim\n")
    terminalWrite("Kernel: Bare metal Nim\n")
    terminalWrite("Shell: PooShell (Nim)\n")

  elif strcmp(cmd, "halt"):
    terminalSetColor(Yellow, Black)
    terminalWrite("System halted. Reset to reboot.\n")
    while true:
      hlt()

  else:
    terminalSetColor(Red, Black)
    terminalWrite("Unknown command: ")
    terminalWrite(cmd)
    terminalWrite("\n")
    terminalSetColor(White, Black)

# Shell
proc runShell() =
  var cmdBuffer: array[256, char]
  var cmdLen = 0

  terminalSetColor(LightGreen, Black)
  terminalWrite("root@poodillion:~# ")
  terminalSetColor(White, Black)

  while true:
    let c = keyboardGetChar()

    if c == '\0':
      continue

    if c == '\n':
      terminalPutChar('\n')

      # Execute command
      var cmd = ""
      for i in 0 ..< cmdLen:
        cmd.add(cmdBuffer[i])

      handleCommand(cmd)

      # Reset command buffer
      cmdLen = 0

      # Show prompt
      terminalSetColor(LightGreen, Black)
      terminalWrite("root@poodillion:~# ")
      terminalSetColor(White, Black)

    elif c == '\b':
      if cmdLen > 0:
        dec cmdLen
        terminalPutChar('\b')

    else:
      if cmdLen < cmdBuffer.len - 1:
        cmdBuffer[cmdLen] = c
        inc cmdLen
        terminalPutChar(c)

# Kernel entry point (called from boot.asm)
proc kernel_main*() {.exportc.} =
  # Initialize terminal
  terminalClear()

  # Boot message
  terminalSetColor(LightGreen, Black)
  terminalWrite("PoodillionOS v0.2.0 - Nim Edition!\n")
  terminalWrite("===================================\n\n")

  terminalSetColor(White, Black)
  terminalWrite("Kernel: Nim (compiled to C)\n")
  terminalWrite("Bootloader: Custom x86 ASM\n")
  terminalWrite("Architecture: i386\n\n")

  terminalSetColor(LightCyan, Black)
  terminalWrite("Welcome to PooShell!\n")
  terminalWrite("Type 'help' for commands.\n\n")

  terminalSetColor(White, Black)

  # Run shell
  runShell()

{.pop.}
