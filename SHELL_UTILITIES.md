# BrainhairOS Shell Scripting Utilities

This document describes the shell scripting utilities built in Brainhair for BrainhairOS.

## Overview

Five essential shell scripting utilities have been implemented:

1. **test** - Evaluate conditional expressions
2. **expr** - Evaluate arithmetic and comparison expressions
3. **which** - Locate commands in PATH
4. **xargs** - Build and execute command lines from stdin
5. **env** - Run programs in modified environments

All utilities are written in Brainhair and compiled to native 32-bit x86 binaries.

## Utilities Reference

### test - Conditional Expression Evaluator

Evaluates conditional expressions and returns exit code 0 (true) or 1 (false).

**Usage:**
```bash
test EXPRESSION
[ EXPRESSION ]
```

**File Tests:**
- `-e FILE` - File exists
- `-f FILE` - File is a regular file
- `-d FILE` - File is a directory
- `-r FILE` - File is readable
- `-w FILE` - File is writable
- `-x FILE` - File is executable
- `-s FILE` - File size is greater than zero

**String Tests:**
- `-z STRING` - String is empty
- `-n STRING` - String is non-empty
- `STRING1 = STRING2` - Strings are equal
- `STRING1 != STRING2` - Strings are not equal

**Integer Tests:**
- `INT1 -eq INT2` - Equal
- `INT1 -ne INT2` - Not equal
- `INT1 -lt INT2` - Less than
- `INT1 -le INT2` - Less than or equal
- `INT1 -gt INT2` - Greater than
- `INT1 -ge INT2` - Greater than or equal

**Examples:**
```bash
./bin/test -f ./bin/ls && echo "File exists"
./bin/test 5 -gt 3 && echo "5 > 3"
./bin/test hello = hello && echo "Match"
[ -d ./bin ] && echo "Directory exists"
```

**Implementation Details:**
- Uses SYS_lstat (107) for file attribute checks
- Uses SYS_access (33) for permission checks
- Supports both `test` and `[` invocations
- File path: `/home/david/brainhair2/userland/test.nim`
- Binary size: 17KB

---

### expr - Expression Evaluator

Evaluates arithmetic and comparison expressions and prints the result.

**Usage:**
```bash
expr ARG1 OP ARG2
```

**Arithmetic Operators:**
- `+` - Addition
- `-` - Subtraction
- `*` - Multiplication (escape with `\*` in shell)
- `/` - Division
- `%` - Modulo

**Comparison Operators:**
- `=` - String equality (returns 1 or 0)
- `!=` - String inequality
- `<` - Numeric less than
- `<=` - Less than or equal
- `>` - Greater than
- `>=` - Greater than or equal

**Examples:**
```bash
./bin/expr 2 + 3          # Output: 5
./bin/expr 10 - 3         # Output: 7
./bin/expr 6 \* 7         # Output: 42
./bin/expr 15 / 3         # Output: 5
./bin/expr 17 % 5         # Output: 2
./bin/expr 5 \< 10        # Output: 1 (true)
./bin/expr hello = hello  # Output: 1 (true)
```

**Use Cases:**
```bash
# Loop counter
i=$(./bin/expr $i + 1)

# Calculate factorial
result=$(./bin/expr $result \* $i)

# Range checking
if [ $(./bin/expr $val \> 10) -eq 1 ]; then
    echo "Value exceeds threshold"
fi
```

**Implementation Details:**
- Integer arithmetic using 32-bit operations
- Proper modulo operator (%) support
- Division by zero protection
- File path: `/home/david/brainhair2/userland/expr.nim`
- Binary size: 12KB

---

### which - Command Locator

Locates executable commands in the PATH and prints their full path.

**Usage:**
```bash
which COMMAND
```

**Search Paths:**
1. `./bin/` - Current directory bin folder
2. `/bin/` - System binaries
3. `/usr/bin/` - User binaries

**Examples:**
```bash
./bin/which ls      # Output: ./bin/ls
./bin/which cat     # Output: ./bin/cat
./bin/which bash    # Output: /bin/bash
```

**Exit Codes:**
- 0 - Command found
- 1 - Command not found

**Implementation Details:**
- Uses SYS_access (33) with X_OK to check executability
- Simple PATH implementation for BrainhairOS
- File path: `/home/david/brainhair2/userland/which.nim`
- Binary size: 10KB

---

### xargs - Command Line Builder

Reads lines from stdin and executes a command with each line as an argument.

**Usage:**
```bash
xargs COMMAND
```

**Examples:**
```bash
# Echo each line with a prefix
echo -e "hello\nworld" | ./bin/xargs ./bin/echo prefix
# Output:
# prefix hello
# prefix world

# Process file list
cat files.txt | ./bin/xargs ./bin/cat

# Chain utilities
./bin/ls | ./bin/xargs ./bin/which
```

**Implementation Details:**
- Uses SYS_fork (2) and SYS_execve (11) for process creation
- Uses SYS_wait4 (114) to wait for child processes
- Reads line-by-line from stdin
- Maximum line length: 4096 bytes
- File path: `/home/david/brainhair2/userland/xargs.nim`
- Binary size: 10KB

---

### env - Environment Manager

Prints environment variables or runs commands with modified environment.

**Usage:**
```bash
env                    # Print all environment variables
env VAR=VAL COMMAND    # Run command with custom environment
```

**Examples:**
```bash
# Print environment
./bin/env | head -5

# Run with custom variables
./bin/env DEBUG=1 LOGLEVEL=verbose ./bin/echo "Testing"

# Multiple variables
./bin/env PATH=/custom/path HOME=/root ./bin/which ls

# Just set variables (no command)
./bin/env MYVAR=hello MYVAL=123
```

**Implementation Details:**
- Reads environment from `/proc/self/environ`
- Uses SYS_execve (11) with custom environment pointer
- Supports multiple VAR=VAL assignments
- File path: `/home/david/brainhair2/userland/env.nim`
- Binary size: 11KB

---

## Building

All utilities can be built with:

```bash
make shell-utils
```

This compiles all five utilities to `/home/david/brainhair2/bin/`.

Individual utilities can be built:
```bash
make bin/test
make bin/expr
make bin/which
make bin/xargs
make bin/env
```

## Testing

Run the comprehensive test suite:

```bash
./test_shell_utils.sh
```

Or run the interactive demo:

```bash
./demo_shell_script.sh
```

## Brainhair Implementation Notes

All utilities follow Brainhair constraints:

1. **No array types** - Use brk allocation for buffers
2. **No int64 in function params** - Only int32, uint32, uint8, ptr
3. **Use % for modulo** - Not the `mod` keyword
4. **No continue keyword** - Restructured loops with if statements
5. **32-bit syscalls** - All syscalls via int 0x80 (Linux x86)
6. **Command-line args** - Via get_argc() and get_argv(i)

## Integration with Shell Scripts

These utilities enable POSIX-style shell scripting:

```bash
#!/bin/bash

# Check prerequisites
for util in test expr which; do
    if ./bin/test -x ./bin/$util; then
        echo "✓ $util available"
    else
        echo "✗ Missing: $util"
        exit 1
    fi
done

# Calculate something
result=$(./bin/expr 10 \* 5)
echo "Result: $result"

# Conditional execution
if ./bin/test $result -gt 40; then
    echo "Threshold exceeded!"
fi

# Batch processing
echo -e "file1\nfile2\nfile3" | ./bin/xargs ./bin/cat
```

## File Locations

**Source files:**
- `/home/david/brainhair2/userland/test.nim`
- `/home/david/brainhair2/userland/expr.nim`
- `/home/david/brainhair2/userland/which.nim`
- `/home/david/brainhair2/userland/xargs.nim`
- `/home/david/brainhair2/userland/env.nim`

**Binaries:**
- `/home/david/brainhair2/bin/test` (17KB)
- `/home/david/brainhair2/bin/expr` (12KB)
- `/home/david/brainhair2/bin/which` (10KB)
- `/home/david/brainhair2/bin/xargs` (10KB)
- `/home/david/brainhair2/bin/env` (11KB)

**Test scripts:**
- `/home/david/brainhair2/test_shell_utils.sh` - Comprehensive test suite
- `/home/david/brainhair2/demo_shell_script.sh` - Interactive demonstrations

## Syscalls Used

| Utility | Syscalls |
|---------|----------|
| test    | SYS_lstat (107), SYS_access (33), SYS_brk (45) |
| expr    | SYS_write (4), SYS_exit (1), SYS_brk (45) |
| which   | SYS_access (33), SYS_brk (45) |
| xargs   | SYS_fork (2), SYS_execve (11), SYS_wait4 (114), SYS_read (3), SYS_brk (45) |
| env     | SYS_open (5), SYS_read (3), SYS_close (6), SYS_execve (11), SYS_brk (45) |

## Makefile Integration

The utilities are integrated into the main Makefile as a new category:

```makefile
# Shell scripting utilities
SHELL_SCRIPT_UTILS = $(BIN_DIR)/test $(BIN_DIR)/expr $(BIN_DIR)/which $(BIN_DIR)/xargs $(BIN_DIR)/env

.PHONY: shell-utils
shell-utils: $(SHELL_SCRIPT_UTILS)
	@echo "✓ Shell scripting utilities built!"
```

They are also included in the `userland` target to build all utilities.

## Future Enhancements

Possible additions:
- Support for logical operators in test (-a, -o, !)
- More complex xargs modes (max args, delimiter control)
- PATH environment variable parsing in which
- Expression precedence and parentheses in expr
- Bracket notation support: [ EXPR ] as alias for test

---

**Project:** BrainhairOS
**Phase:** Shell Scripting Utilities
**Language:** Brainhair
**Architecture:** x86 32-bit Linux
