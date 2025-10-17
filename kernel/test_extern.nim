# Test External Function Calls in Mini-Nim
# This kernel calls the serial_print function from assembly

# Declare external functions from assembly
extern proc serial_print(msg: ptr uint8)
extern proc serial_putchar(ch: uint8)

proc main() =
  # Print a message using the external serial_print function
  # Note: We need to put strings in .data section
  # For now, write to VGA to test that main() runs
  cast[ptr uint8](0xB8000)[0] = cast[uint8]('E')
  cast[ptr uint8](0xB8001)[0] = cast[uint8](0x0A)  # Green

  cast[ptr uint8](0xB8002)[0] = cast[uint8]('X')
  cast[ptr uint8](0xB8003)[0] = cast[uint8](0x0A)

  cast[ptr uint8](0xB8004)[0] = cast[uint8]('T')
  cast[ptr uint8](0xB8005)[0] = cast[uint8](0x0A)

  cast[ptr uint8](0xB8006)[0] = cast[uint8]('!')
  cast[ptr uint8](0xB8007)[0] = cast[uint8](0x0A)

  while true:
    discard
