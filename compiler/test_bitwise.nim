# Test hex literals and bitwise operators

proc main() =
  var addr: uint32 = 0xB8000
  var color: uint8 = 2
  var bg: uint8 = 0

  # Test bitwise OR
  var result1: uint8 = color | bg

  # Test bitwise shift
  var shifted: uint8 = bg << 4

  # Test combined
  var combined: uint8 = color | shifted

  # Test cast with hex
  var ptr_val: uint32 = 0xB8000
