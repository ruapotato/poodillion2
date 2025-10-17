# Mini-Nim Kernel with Serial Output
# Writes to COM1 serial port (0x3F8) for terminal display

proc main() =
  # Note: We'll need to add inline assembly support to Mini-Nim
  # For now, let's write a message that can be seen via serial
  # We'll write the assembly version directly

  # Simple version: just write to VGA for now
  # TODO: Add serial port support
  cast[ptr uint8](0xB8000)[0] = cast[uint8]('M')
  cast[ptr uint8](0xB8001)[0] = cast[uint8](0x0A)  # Green

  cast[ptr uint8](0xB8002)[0] = cast[uint8]('I')
  cast[ptr uint8](0xB8003)[0] = cast[uint8](0x0A)

  cast[ptr uint8](0xB8004)[0] = cast[uint8]('N')
  cast[ptr uint8](0xB8005)[0] = cast[uint8](0x0A)

  cast[ptr uint8](0xB8006)[0] = cast[uint8]('I')
  cast[ptr uint8](0xB8007)[0] = cast[uint8](0x0A)

  # Halt
  while true:
    discard
