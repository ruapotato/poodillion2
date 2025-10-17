# Test String Literals with External Functions
# This tests that strings are placed in .data section correctly

# Declare external serial output function
extern proc serial_print(msg: ptr uint8)

proc main() =
  # Test string literal - should be placed in data section
  serial_print(cast[ptr uint8]("Hello from Mini-Nim!\n"))
  serial_print(cast[ptr uint8]("String literals work!\n"))

  # Infinite loop
  while true:
    discard
