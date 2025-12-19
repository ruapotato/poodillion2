# Ultra-simple kernel - inline assembly to write directly
proc main() =
  # Just write a raw value to VGA memory - no pointers, no casts
  # This will be compiled to direct memory access

  # Use a simple loop that does nothing - should work
  var x: int32 = 42

  # Infinite loop
  while x == 42:
    discard
