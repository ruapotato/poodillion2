# grep - Search for patterns in files
# Usage: grep [OPTIONS] PATTERN [FILE...]
# Options:
#   -i    Case insensitive search
#   -v    Invert match (select non-matching lines)
#   -n    Show line numbers
#   -c    Count matching lines
#   -l    List filenames with matches only
#   -h    Suppress filename prefix (default with single file)

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

# String utilities
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

# Compare strings
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s2[i] == cast[uint8](0):
      return 1
    if s1[i] != s2[i]:
      if s1[i] < s2[i]:
        return -1
      return 1
    i = i + 1
  if s2[i] == cast[uint8](0):
    return 0
  return -1

# Convert to lowercase
proc to_lower(c: uint8): uint8 =
  if c >= cast[uint8](65):
    if c <= cast[uint8](90):
      return c + cast[uint8](32)
  return c

# Print integer
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)

  var num: int32 = n
  var i: int32 = 0

  while num > 0:
    var digit: int32 = num % 10
    buffer[i] = cast[uint8](48 + digit)
    num = num / 10
    i = i + 1

  var j: int32 = i - 1
  while j >= 0:
    discard syscall3(SYS_write, STDOUT, cast[int32](buffer + j), 1)
    j = j - 1

# Simple pattern matching
# Supports:
#   - Literal string matching
#   - . (any character)
#   - * (zero or more of previous character)
#   - ^ (start of line)
#   - $ (end of line)
proc match_pattern(text: ptr uint8, text_len: int32, pattern: ptr uint8, pattern_len: int32, case_insensitive: int32): int32 =
  # Handle empty pattern
  if pattern_len == 0:
    return 1

  # Check for ^ (start of line anchor)
  var has_start_anchor: int32 = 0
  var pat_start: int32 = 0
  if pattern[0] == cast[uint8](94):  # ^
    has_start_anchor = 1
    pat_start = 1

  # Check for $ (end of line anchor)
  var has_end_anchor: int32 = 0
  var pat_end: int32 = pattern_len
  if pattern[pattern_len - 1] == cast[uint8](36):  # $
    has_end_anchor = 1
    pat_end = pattern_len - 1

  # If both anchors, must match exactly
  if has_start_anchor == 1:
    if has_end_anchor == 1:
      # Must match entire line
      var effective_pat_len: int32 = pat_end - pat_start
      if text_len != effective_pat_len:
        return 0

      var i: int32 = 0
      while i < effective_pat_len:
        var tc: uint8 = text[i]
        var pc: uint8 = pattern[pat_start + i]

        if case_insensitive == 1:
          tc = to_lower(tc)
          pc = to_lower(pc)

        if pc == cast[uint8](46):  # .
          i = i + 1
        else:
          if tc != pc:
            return 0
          i = i + 1

      return 1

  # Try to match pattern at each position
  var start_pos: int32 = 0
  var max_pos: int32 = text_len

  if has_start_anchor == 1:
    max_pos = 1  # Only try position 0

  while start_pos < max_pos:
    var matched: int32 = 1
    var text_idx: int32 = start_pos
    var pat_idx: int32 = pat_start

    while pat_idx < pat_end:
      # Check for * operator
      if pat_idx + 1 < pat_end:
        if pattern[pat_idx + 1] == cast[uint8](42):  # *
          # Match zero or more of current character
          var match_char: uint8 = pattern[pat_idx]
          pat_idx = pat_idx + 2

          # Try matching zero occurrences first
          var saved_text_idx: int32 = text_idx

          # Then try matching one or more
          while text_idx < text_len:
            var tc: uint8 = text[text_idx]
            var mc: uint8 = match_char

            if case_insensitive == 1:
              tc = to_lower(tc)
              mc = to_lower(mc)

            if mc == cast[uint8](46):  # . matches any
              text_idx = text_idx + 1
            else:
              if tc != mc:
                break
              text_idx = text_idx + 1

          # Continue with rest of pattern
        else:
          # Normal character match
          if text_idx >= text_len:
            matched = 0
            break

          var tc: uint8 = text[text_idx]
          var pc: uint8 = pattern[pat_idx]

          if case_insensitive == 1:
            tc = to_lower(tc)
            pc = to_lower(pc)

          if pc == cast[uint8](46):  # .
            text_idx = text_idx + 1
            pat_idx = pat_idx + 1
          else:
            if tc != pc:
              matched = 0
              break
            text_idx = text_idx + 1
            pat_idx = pat_idx + 1
      else:
        # Normal character match (last char or no * following)
        if text_idx >= text_len:
          matched = 0
          break

        var tc: uint8 = text[text_idx]
        var pc: uint8 = pattern[pat_idx]

        if case_insensitive == 1:
          tc = to_lower(tc)
          pc = to_lower(pc)

        if pc == cast[uint8](46):  # .
          text_idx = text_idx + 1
          pat_idx = pat_idx + 1
        else:
          if tc != pc:
            matched = 0
            break
          text_idx = text_idx + 1
          pat_idx = pat_idx + 1

    # Check if we matched the whole pattern
    if matched == 1:
      if pat_idx == pat_end:
        # If end anchor, must be at end of line
        if has_end_anchor == 1:
          if text_idx == text_len:
            return 1
        else:
          return 1

    start_pos = start_pos + 1

  return 0

# Process a file
proc grep_file(fd: int32, filename: ptr uint8, pattern: ptr uint8, pattern_len: int32, case_insensitive: int32, invert: int32, show_line_numbers: int32, count_only: int32, list_files: int32, show_filename: int32, buffer: ptr uint8, line_buffer: ptr uint8): int32 =
  var line_num: int32 = 0
  var match_count: int32 = 0
  var buffer_pos: int32 = 0
  var buffer_size: int32 = 0
  var line_len: int32 = 0
  var has_match: int32 = 0

  var reading: int32 = 1
  while reading == 1:
    # Refill buffer if needed
    if buffer_pos >= buffer_size:
      buffer_size = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
      if buffer_size <= 0:
        reading = 0
        # Process final line if no newline at end
        if line_len > 0:
          line_num = line_num + 1
          var matches: int32 = match_pattern(line_buffer, line_len, pattern, pattern_len, case_insensitive)
          if invert == 1:
            if matches == 0:
              matches = 1
            else:
              matches = 0

          if matches == 1:
            match_count = match_count + 1
            has_match = 1
            if count_only == 0:
              if list_files == 0:
                if show_filename == 1:
                  print(filename)
                  discard syscall3(SYS_write, STDOUT, cast[int32](":"), 1)
                if show_line_numbers == 1:
                  print_int(line_num)
                  discard syscall3(SYS_write, STDOUT, cast[int32](":"), 1)
                discard syscall3(SYS_write, STDOUT, cast[int32](line_buffer), line_len)
                discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
        break
      buffer_pos = 0

    # Read character by character, building lines
    var c: uint8 = buffer[buffer_pos]
    buffer_pos = buffer_pos + 1

    if c == cast[uint8](10):  # newline
      line_num = line_num + 1

      # Check if line matches pattern
      var matches: int32 = match_pattern(line_buffer, line_len, pattern, pattern_len, case_insensitive)
      if invert == 1:
        if matches == 0:
          matches = 1
        else:
          matches = 0

      if matches == 1:
        match_count = match_count + 1
        has_match = 1
        if count_only == 0:
          if list_files == 0:
            if show_filename == 1:
              print(filename)
              discard syscall3(SYS_write, STDOUT, cast[int32](":"), 1)
            if show_line_numbers == 1:
              print_int(line_num)
              discard syscall3(SYS_write, STDOUT, cast[int32](":"), 1)
            discard syscall3(SYS_write, STDOUT, cast[int32](line_buffer), line_len)
            discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

      line_len = 0
    else:
      # Add to line buffer
      if line_len < 4096:
        line_buffer[line_len] = c
        line_len = line_len + 1

  # Output results
  if count_only == 1:
    if show_filename == 1:
      print(filename)
      discard syscall3(SYS_write, STDOUT, cast[int32](":"), 1)
    print_int(match_count)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  else:
    if list_files == 1:
      if has_match == 1:
        print(filename)
        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  return match_count

proc main() =
  var argc: int32 = get_argc()

  if argc < 2:
    print_err(cast[ptr uint8]("Usage: grep [OPTIONS] PATTERN [FILE...]\n"))
    print_err(cast[ptr uint8]("Options:\n"))
    print_err(cast[ptr uint8]("  -i    Case insensitive\n"))
    print_err(cast[ptr uint8]("  -v    Invert match\n"))
    print_err(cast[ptr uint8]("  -n    Show line numbers\n"))
    print_err(cast[ptr uint8]("  -c    Count matches\n"))
    print_err(cast[ptr uint8]("  -l    List files with matches\n"))
    print_err(cast[ptr uint8]("  -h    Hide filename\n"))
    discard syscall1(SYS_exit, 1)

  # Parse options
  var case_insensitive: int32 = 0
  var invert: int32 = 0
  var show_line_numbers: int32 = 0
  var count_only: int32 = 0
  var list_files: int32 = 0
  var hide_filename: int32 = 0
  var pattern: ptr uint8 = cast[ptr uint8](0)
  var pattern_idx: int32 = 0

  # Allocate memory for file list
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var line_buffer: ptr uint8 = cast[ptr uint8](old_brk + 4096)
  var files: ptr int32 = cast[ptr int32](old_brk + 8192)
  var file_count: int32 = 0

  var i: int32 = 1
  while i < argc:
    var arg: ptr uint8 = get_argv(i)

    # Check for options
    if arg[0] == cast[uint8](45):  # -
      var j: int32 = 1
      while arg[j] != cast[uint8](0):
        if arg[j] == cast[uint8](105):  # i
          case_insensitive = 1
        if arg[j] == cast[uint8](118):  # v
          invert = 1
        if arg[j] == cast[uint8](110):  # n
          show_line_numbers = 1
        if arg[j] == cast[uint8](99):  # c
          count_only = 1
        if arg[j] == cast[uint8](108):  # l
          list_files = 1
        if arg[j] == cast[uint8](104):  # h
          hide_filename = 1
        j = j + 1
    else:
      # First non-option is pattern
      if pattern == cast[ptr uint8](0):
        pattern = arg
        pattern_idx = i
      else:
        # Rest are files
        files[file_count] = i
        file_count = file_count + 1

    i = i + 1

  if pattern == cast[ptr uint8](0):
    print_err(cast[ptr uint8]("grep: no pattern specified\n"))
    discard syscall1(SYS_exit, 1)

  var pattern_len: int32 = strlen(pattern)

  # Determine if we should show filenames
  var show_filename: int32 = 0
  if file_count > 1:
    show_filename = 1
  if hide_filename == 1:
    show_filename = 0

  # Process files or stdin
  if file_count == 0:
    # Read from stdin
    discard grep_file(STDIN, cast[ptr uint8]("(standard input)"), pattern, pattern_len, case_insensitive, invert, show_line_numbers, count_only, list_files, 0, buffer, line_buffer)
  else:
    var exit_code: int32 = 0
    var total_matches: int32 = 0

    var fi: int32 = 0
    while fi < file_count:
      var arg_idx: int32 = files[fi]
      var filename: ptr uint8 = get_argv(arg_idx)

      var fd: int32 = syscall2(SYS_open, cast[int32](filename), O_RDONLY)
      if fd < 0:
        print_err(cast[ptr uint8]("grep: "))
        print_err(filename)
        print_err(cast[ptr uint8](": cannot open file\n"))
        exit_code = 2
      else:
        var matches: int32 = grep_file(fd, filename, pattern, pattern_len, case_insensitive, invert, show_line_numbers, count_only, list_files, show_filename, buffer, line_buffer)
        total_matches = total_matches + matches
        discard syscall1(SYS_close, fd)

      fi = fi + 1

    if exit_code == 0:
      if total_matches == 0:
        exit_code = 1

    discard syscall1(SYS_exit, exit_code)

  discard syscall1(SYS_exit, 0)
