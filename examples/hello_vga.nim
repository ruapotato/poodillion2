# hello_vga.nim - First Mini-Nim program!
# Bare metal VGA Hello World

proc main() =
  var vga: ptr uint16 = cast[ptr uint16](0xB8000)
  var msg: ptr uint8 = cast[ptr uint8](0)  # We'll handle strings differently

  # Write directly to VGA: "Mini-Nim!"
  # Each character is: char | (color << 8)
  # Color: 0x0A = light green on black

  vga[0] = 77 + 0x0A00    # M
  vga[1] = 105 + 0x0A00   # i
  vga[2] = 110 + 0x0A00   # n
  vga[3] = 105 + 0x0A00   # i
  vga[4] = 45 + 0x0A00    # -
  vga[5] = 78 + 0x0A00    # N
  vga[6] = 105 + 0x0A00   # i
  vga[7] = 109 + 0x0A00   # m
  vga[8] = 33 + 0x0A00    # !

  # Fill rest of first line with colored spaces
  var i: int32 = 9
  while i < 80:
    vga[i] = 32 + 0x1F00  # Space, white on blue
    i = i + 1
