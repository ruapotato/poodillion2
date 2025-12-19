# Minimal test kernel - just write one character
proc main() =
  # Write 'X' directly to VGA memory
  var vga: ptr uint16 = cast[ptr uint16](0xB8000)
  vga[0] = 0x0F58  # 'X' with white color

  # Infinite halt loop
  while true:
    discard
