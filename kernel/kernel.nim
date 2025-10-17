# PoodillionOS Kernel - Written in Mini-Nim!
# This kernel will be compiled by our custom Mini-Nim compiler

# VGA text mode constants
const VGA_MEMORY: uint32 = 0xB8000
const VGA_WIDTH: int32 = 80
const VGA_HEIGHT: int32 = 25

# VGA Colors
const COLOR_BLACK: uint8 = 0
const COLOR_GREEN: uint8 = 2
const COLOR_CYAN: uint8 = 3
const COLOR_WHITE: uint8 = 15

# Global terminal state
var terminal_row: int32
var terminal_column: int32
var terminal_color: uint8

# Pack foreground and background colors into VGA color byte
# color = fg | (bg << 4)
proc vga_entry_color(fg: uint8, bg: uint8): uint8 =
  var result: uint8 = fg
  var shifted: uint8 = bg << 4
  result = result | shifted
  return result

# Pack character and color into VGA entry
# entry = c | (color << 8)
proc vga_entry(c: char, color: uint8): uint16 =
  var char_val: uint16 = cast[uint16](c)
  var color_val: uint16 = cast[uint16](color)
  var shifted: uint16 = color_val << 8
  var result: uint16 = char_val | shifted
  return result

# Initialize terminal
proc terminal_initialize() =
  terminal_row = 0
  terminal_column = 0
  terminal_color = vga_entry_color(COLOR_GREEN, COLOR_BLACK)

  # Cast VGA memory address to pointer
  var vga: ptr uint16 = cast[ptr uint16](VGA_MEMORY)

  # Clear screen
  for y in 0..VGA_HEIGHT - 1:
    for x in 0..VGA_WIDTH - 1:
      var index: int32 = y * VGA_WIDTH + x
      vga[index] = vga_entry(' ', terminal_color)

# Put character at specific position
proc terminal_putentryat(c: char, color: uint8, x: int32, y: int32) =
  var vga: ptr uint16 = cast[ptr uint16](VGA_MEMORY)
  var index: int32 = y * VGA_WIDTH + x
  vga[index] = vga_entry(c, color)

# Write a string to terminal (simplified version)
proc terminal_writestr(msg: ptr char, len: int32, row: int32) =
  var color: uint8 = vga_entry_color(COLOR_GREEN, COLOR_BLACK)
  for i in 0..len - 1:
    terminal_putentryat(msg[i], color, i, row)

# Kernel main entry point
proc main() =
  # Initialize terminal
  terminal_initialize()

  # Write "PoodillionOS" character by character
  var color1: uint8 = vga_entry_color(COLOR_GREEN, COLOR_BLACK)
  var color2: uint8 = vga_entry_color(COLOR_CYAN, COLOR_BLACK)
  var color3: uint8 = vga_entry_color(COLOR_WHITE, COLOR_BLACK)

  # Row 0: "PoodillionOS v0.1"
  terminal_putentryat('P', color1, 0, 0)
  terminal_putentryat('o', color1, 1, 0)
  terminal_putentryat('o', color1, 2, 0)
  terminal_putentryat('d', color1, 3, 0)
  terminal_putentryat('i', color1, 4, 0)
  terminal_putentryat('l', color1, 5, 0)
  terminal_putentryat('l', color1, 6, 0)
  terminal_putentryat('i', color1, 7, 0)
  terminal_putentryat('o', color1, 8, 0)
  terminal_putentryat('n', color1, 9, 0)
  terminal_putentryat('O', color1, 10, 0)
  terminal_putentryat('S', color1, 11, 0)
  terminal_putentryat(' ', color1, 12, 0)
  terminal_putentryat('v', color1, 13, 0)
  terminal_putentryat('0', color1, 14, 0)
  terminal_putentryat('.', color1, 15, 0)
  terminal_putentryat('1', color1, 16, 0)

  # Row 2: "Kernel: Mini-Nim!"
  terminal_putentryat('K', color2, 0, 2)
  terminal_putentryat('e', color2, 1, 2)
  terminal_putentryat('r', color2, 2, 2)
  terminal_putentryat('n', color2, 3, 2)
  terminal_putentryat('e', color2, 4, 2)
  terminal_putentryat('l', color2, 5, 2)
  terminal_putentryat(':', color2, 6, 2)
  terminal_putentryat(' ', color2, 7, 2)
  terminal_putentryat('M', color2, 8, 2)
  terminal_putentryat('i', color2, 9, 2)
  terminal_putentryat('n', color2, 10, 2)
  terminal_putentryat('i', color2, 11, 2)
  terminal_putentryat('-', color2, 12, 2)
  terminal_putentryat('N', color2, 13, 2)
  terminal_putentryat('i', color2, 14, 2)
  terminal_putentryat('m', color2, 15, 2)
  terminal_putentryat('!', color2, 16, 2)

  # Row 4: "Booted successfully!"
  terminal_putentryat('B', color3, 0, 4)
  terminal_putentryat('o', color3, 1, 4)
  terminal_putentryat('o', color3, 2, 4)
  terminal_putentryat('t', color3, 3, 4)
  terminal_putentryat('e', color3, 4, 4)
  terminal_putentryat('d', color3, 5, 4)
  terminal_putentryat(' ', color3, 6, 4)
  terminal_putentryat('O', color3, 7, 4)
  terminal_putentryat('K', color3, 8, 4)
  terminal_putentryat('!', color3, 9, 4)

  # Halt CPU (infinite loop)
  while true:
    discard
    # We'll need inline asm: hlt
