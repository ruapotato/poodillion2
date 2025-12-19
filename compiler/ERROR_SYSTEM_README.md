# Brainhair Compiler - Error Handling System

## Overview

This directory contains a comprehensive, production-quality error handling system for the Brainhair compiler. The system provides structured error reporting with source location tracking, colorized output, error codes, and helpful diagnostic messages.

## Files

### Core Implementation

- **`errors.py`** (637 lines)
  - Main error handling implementation
  - Contains all error types, SourceSpan, and ErrorReporter
  - Production-ready with complete docstrings

### Documentation

- **`ERROR_HANDLING_GUIDE.md`**
  - Complete user guide for the error handling system
  - API documentation for all error types
  - Examples of error output
  - Best practices

- **`INTEGRATION_GUIDE.md`**
  - Step-by-step guide for integrating error handling into existing compiler
  - Before/after code examples
  - Error recovery strategies
  - Testing approach

- **`ERROR_SYSTEM_README.md`** (this file)
  - Quick overview and navigation guide

### Examples and Tests

- **`test_errors.py`** (8.5 KB)
  - Comprehensive demonstration of all error types
  - Shows colorized output for errors and warnings
  - Run with: `python3 test_errors.py`

- **`example_usage.py`** (9.6 KB)
  - Shows integration with compiler phases
  - Demonstrates error recovery and reporting
  - Mock compiler pipeline example
  - Run with: `python3 example_usage.py`

## Quick Start

### Basic Usage

```python
from errors import ErrorReporter, TypeError, SourceSpan

# Create error reporter
reporter = ErrorReporter()

# Create source location
span = SourceSpan(
    file="example.bh",
    line=10,
    column=5,
    end_column=12,
    source_line='let x: i32 = "hello";'
)

# Report an error
error = TypeError.type_mismatch("i32", "str", span)
reporter.add_error(error)

# Print all errors
reporter.print_report()
```

### Example Output

```
error[T001]: type mismatch: expected 'i32', found 'str'
  --> example.bh:10:5

  10 | let x: i32 = "hello";
              ^^^^^^^^

1 error generated
```

## Features

### 1. Structured Error Types

Five main error categories for different compilation phases:

- **LexerError** - Invalid characters, unterminated strings, malformed numbers
- **ParseError** - Unexpected tokens, missing delimiters, syntax errors
- **TypeError** - Type mismatches, unknown types, invalid operations
- **OwnershipError** - Use after move, double free, borrow conflicts
- **NameError** - Undefined variables, duplicate definitions

Plus **CompilerWarning** for non-fatal issues.

### 2. Source Location Tracking

The `SourceSpan` class tracks:
- File name
- Line and column numbers (start and end)
- Actual source code line for context display

### 3. Error Reporter

The `ErrorReporter` class:
- Collects multiple errors/warnings
- Formats them with color and context
- Provides summary statistics
- Supports both colored and plain text output

### 4. Error Codes

Each error has a unique code (e.g., `L001`, `P002`, `T001`) for:
- Documentation lookup
- Error suppression
- Automated testing

### 5. Colorized Output

- Errors in red
- Warnings in yellow
- Location info in blue
- Notes in cyan
- Can be disabled for non-terminal output

### 6. Rich Context

Each error can include:
- Main error message
- Source location with caret pointing to error
- Additional notes with helpful hints
- References to related locations (e.g., where value was moved)

## Error Type Reference

| Category | Error Codes | Examples |
|----------|-------------|----------|
| Lexer | L001-L099 | Invalid character, unterminated string |
| Parser | P001-P099 | Unexpected token, missing delimiter |
| Type | T001-T099 | Type mismatch, unknown type |
| Ownership | O001-O099 | Use after move, borrow conflict |
| Name | N001-N099 | Undefined variable, duplicate definition |
| Warnings | W001-W099 | Unused variable, unreachable code |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 CompilerError                        │
│  - message: str                                      │
│  - span: Optional[SourceSpan]                        │
│  - error_code: Optional[str]                         │
│  - notes: List[str]                                  │
│  - format() -> str                                   │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────┴────────────┬──────────────────┐
        │                        │                  │
┌───────▼────────┐   ┌──────────▼──────┐   ┌───────▼────────┐
│  LexerError    │   │  ParseError     │   │  TypeError     │
├────────────────┤   ├─────────────────┤   ├────────────────┤
│ - invalid_char │   │ - unexpected_   │   │ - type_        │
│ - unterm_str   │   │   token         │   │   mismatch     │
│ - invalid_num  │   │ - missing_delim │   │ - unknown_type │
└────────────────┘   └─────────────────┘   └────────────────┘

┌─────────────────────────────────────────────────────┐
│               ErrorReporter                          │
│  - errors: List[CompilerError]                       │
│  - warnings: List[CompilerWarning]                   │
│  + add_error(error)                                  │
│  + has_errors() -> bool                              │
│  + report() -> str                                   │
│  + print_report()                                    │
└─────────────────────────────────────────────────────┘
```

## Running Tests

### Full Test Suite
```bash
cd /home/david/poodillion2/compiler
python3 test_errors.py
```

This will display examples of all error types with full colorized output.

### Example Usage
```bash
python3 example_usage.py
```

This shows how to integrate the error system into a compiler pipeline.

## Integration Steps

To integrate this error handling system into the Brainhair compiler:

1. Read `INTEGRATION_GUIDE.md` for detailed steps
2. Update `Token` class to include span information
3. Modify `Lexer` to accept and use `ErrorReporter`
4. Modify `Parser` to accept and use `ErrorReporter`
5. Modify `TypeChecker` to accept and use `ErrorReporter`
6. Update main compiler driver to coordinate error reporting
7. Implement error recovery in parser
8. Add tests for error cases

See `INTEGRATION_GUIDE.md` for complete code examples.

## Design Principles

1. **User-Friendly**: Clear messages with source context help users fix issues
2. **Comprehensive**: Report all errors in a phase, not just the first
3. **Recoverable**: Continue compilation after errors to find multiple issues
4. **Extensible**: Easy to add new error types and codes
5. **Testable**: All error types have factory methods for easy testing
6. **Documented**: Every class and method has docstrings
7. **Professional**: Follows Rust/Clang style error reporting conventions

## Error Message Format

```
<severity>[<code>]: <message>
  --> <file>:<line>:<column>

  <line_num> | <source_line>
              <caret>

  note: <additional_context>
```

Example:
```
error[T001]: type mismatch: expected 'i32', found 'str'
  --> example.bh:10:14

  10 | let x: i32 = "hello";
                    ^^^^^^^^

1 error generated
```

## Comparison with Other Compilers

This system is inspired by modern compiler error reporting:

| Feature | Rustc | Clang | GCC | Brainhair |
|---------|-------|-------|-----|-----------|
| Error codes | ✓ | ✗ | ✗ | ✓ |
| Source context | ✓ | ✓ | ✓ | ✓ |
| Color output | ✓ | ✓ | ✓ | ✓ |
| Multi-line spans | ✓ | ✓ | ✗ | Future |
| Suggestions | ✓ | ✓ | ✓ | Future |
| JSON output | ✓ | ✗ | ✗ | Future |

## Future Enhancements

Potential improvements:

- [ ] Multi-line error spans
- [ ] "Did you mean?" suggestions
- [ ] JSON output for IDE integration
- [ ] Error suppression via pragmas
- [ ] Localization support
- [ ] Macro expansion tracking
- [ ] Interactive error explorer
- [ ] Error statistics and analytics

## License

Part of the Brainhair compiler project.

## Contributing

When adding new error types:

1. Create static factory methods (e.g., `TypeError.type_mismatch()`)
2. Assign appropriate error codes (follow existing scheme)
3. Include helpful notes when possible
4. Add examples to `test_errors.py`
5. Update documentation

## Questions?

See the documentation files:
- `ERROR_HANDLING_GUIDE.md` - Complete API reference
- `INTEGRATION_GUIDE.md` - How to integrate into compiler
- `example_usage.py` - Working examples

Or run the test suite to see the system in action.
