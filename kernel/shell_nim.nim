# PoodillionOS Mini-Nim Shell
# Full Nim implementation of shell using assembly drivers

# External serial functions from serial.asm
extern proc serial_init()
extern proc serial_print(msg: ptr uint8)
extern proc serial_putchar(ch: uint8)

# Print with newline
proc println(msg: ptr uint8) =
  serial_print(msg)
  serial_putchar(cast[uint8](10))  # newline

# Simple string compare helper
proc str_eq(s1: ptr uint8, s2: ptr uint8): bool =
  var i: int32 = 0
  while true:
    var c1: uint8 = s1[i]
    var c2: uint8 = s2[i]
    if c1 != c2:
      return false
    if c1 == cast[uint8](0):
      return true
    i = i + 1
  return false

# Command: ls
proc cmd_ls() =
  println(cast[ptr uint8]("bin/  home/  root/  usr/  tmp/"))

# Command: cat
proc cmd_cat() =
  println(cast[ptr uint8]("Welcome to PoodillionOS!"))
  println(cast[ptr uint8]("A real operating system written in Mini-Nim"))

# Command: echo
proc cmd_echo() =
  println(cast[ptr uint8]("Echo: Hello from Mini-Nim shell!"))

# Command: help
proc cmd_help() =
  println(cast[ptr uint8]("Available commands:"))
  println(cast[ptr uint8]("  ls    - List files"))
  println(cast[ptr uint8]("  cat   - Display file"))
  println(cast[ptr uint8]("  echo  - Print text"))
  println(cast[ptr uint8]("  help  - Show this help"))

# Main shell entry point
proc main() =
  # Initialize serial port
  serial_init()

  # Print banner
  serial_putchar(cast[uint8](10))
  println(cast[ptr uint8]("========================================"))
  println(cast[ptr uint8]("  PoodillionOS v0.1 - Mini-Nim Shell"))
  println(cast[ptr uint8]("========================================"))
  serial_putchar(cast[uint8](10))
  println(cast[ptr uint8]("Built with Mini-Nim compiler!"))
  println(cast[ptr uint8]("Type 'help' for available commands"))
  serial_putchar(cast[uint8](10))

  # Demonstrate commands
  serial_print(cast[ptr uint8]("root@poodillion:~# "))
  println(cast[ptr uint8]("ls"))
  cmd_ls()
  serial_putchar(cast[uint8](10))

  serial_print(cast[ptr uint8]("root@poodillion:~# "))
  println(cast[ptr uint8]("cat welcome.txt"))
  cmd_cat()
  serial_putchar(cast[uint8](10))

  serial_print(cast[ptr uint8]("root@poodillion:~# "))
  println(cast[ptr uint8]("echo"))
  cmd_echo()
  serial_putchar(cast[uint8](10))

  serial_print(cast[ptr uint8]("root@poodillion:~# "))
  println(cast[ptr uint8]("help"))
  cmd_help()
  serial_putchar(cast[uint8](10))

  # Final prompt
  serial_print(cast[ptr uint8]("root@poodillion:~# "))

  # Halt
  while true:
    discard
