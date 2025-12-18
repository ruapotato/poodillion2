# getopt - Parse command line options
# Usage: getopt OPTIONS ARGS...
# Example: getopt "ab:c" -a -b value -c arg1 arg2
# Output: -a -b value -c -- arg1 arg2

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Check if option requires argument (followed by ':' in optstring)
proc option_needs_arg(optstring: ptr uint8, opt: uint8): int32 =
  var i: int32 = 0
  while optstring[i] != cast[uint8](0):
    if optstring[i] == opt:
      if optstring[i + 1] == cast[uint8](58):  # ':'
        return 1
      return 0
    i = i + 1
  return 0

# Check if character is in optstring
proc is_valid_option(optstring: ptr uint8, opt: uint8): int32 =
  var i: int32 = 0
  while optstring[i] != cast[uint8](0):
    if optstring[i] == opt:
      if optstring[i] != cast[uint8](58):  # skip ':'
        return 1
    i = i + 1
  return 0

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    print_err(cast[ptr uint8]("Usage: getopt OPTIONS ARGS...\n"))
    discard syscall1(SYS_exit, 1)

  var optstring: ptr uint8 = get_argv(1)
  var arg_index: int32 = 2
  var first_output: int32 = 1

  # Allocate buffer for output
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 512
  discard syscall1(SYS_brk, new_brk)
  var output: ptr uint8 = cast[ptr uint8](old_brk)

  # Process arguments
  while arg_index < argc:
    var arg: ptr uint8 = get_argv(arg_index)

    # Check if it's an option (starts with -)
    if arg[0] == cast[uint8](45):  # '-'
      if arg[1] == cast[uint8](45):  # '--'
        # End of options marker
        if first_output == 0:
          print(cast[ptr uint8](" "))
        print(cast[ptr uint8]("--"))
        arg_index = arg_index + 1
        break

      # Process short options
      var opt_pos: int32 = 1
      while arg[opt_pos] != cast[uint8](0):
        var opt: uint8 = arg[opt_pos]

        # Validate option
        var is_valid: int32 = is_valid_option(optstring, opt)
        if is_valid == 0:
          print_err(cast[ptr uint8]("getopt: invalid option -- "))
          output[0] = opt
          output[1] = cast[uint8](0)
          print_err(output)
          print_err(cast[ptr uint8]("\n"))
          discard syscall1(SYS_exit, 1)

        # Output option
        if first_output == 0:
          print(cast[ptr uint8](" "))
        first_output = 0
        print(cast[ptr uint8]("-"))
        output[0] = opt
        output[1] = cast[uint8](0)
        print(output)

        # Check if option needs argument
        var needs_arg: int32 = option_needs_arg(optstring, opt)
        if needs_arg != 0:
          if arg[opt_pos + 1] != cast[uint8](0):
            # Argument attached to option
            print(cast[ptr uint8](" "))
            var i: int32 = opt_pos + 1
            var j: int32 = 0
            while arg[i] != cast[uint8](0):
              output[j] = arg[i]
              i = i + 1
              j = j + 1
            output[j] = cast[uint8](0)
            print(output)
            break
          else:
            # Argument in next argv
            arg_index = arg_index + 1
            if arg_index >= argc:
              print_err(cast[ptr uint8]("getopt: option requires an argument -- "))
              output[0] = opt
              output[1] = cast[uint8](0)
              print_err(output)
              print_err(cast[ptr uint8]("\n"))
              discard syscall1(SYS_exit, 1)

            print(cast[ptr uint8](" "))
            print(get_argv(arg_index))
            break

        opt_pos = opt_pos + 1
    else:
      # Non-option argument, end of options
      break

    arg_index = arg_index + 1

  # Output remaining arguments
  if arg_index < argc:
    if first_output == 0:
      print(cast[ptr uint8](" "))
    print(cast[ptr uint8]("--"))

    while arg_index < argc:
      print(cast[ptr uint8](" "))
      print(get_argv(arg_index))
      arg_index = arg_index + 1

  print(cast[ptr uint8]("\n"))
  discard syscall1(SYS_exit, 0)
