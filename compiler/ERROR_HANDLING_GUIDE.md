# Brainhair Compiler Error Handling System

## Overview

The Brainhair compiler includes a comprehensive error handling system that provides:

- **Structured error types** for different compilation phases (lexing, parsing, type checking, etc.)
- **Source location tracking** with file, line, and column information
- **Colorized terminal output** for better readability
- **Error codes** for documentation lookup (e.g., `E001`, `L002`)
- **Context and hints** to help users fix issues
- **Support for warnings** in addition to errors

## Quick Start

### Basic Usage

```python
from compiler.errors import ErrorReporter, TypeError, SourceSpan

# Create an error reporter
reporter = ErrorReporter()

# Create a source span for location tracking
span = SourceSpan(
    file="example.bh",
    line=10,
    column=5,
    end_column=12,
    source_line='let x: i32 = "hello";'
)

# Report a type error
error = TypeError.type_mismatch("i32", "str", span)
reporter.add_error(error)

# Check for errors and print report
if reporter.has_errors():
    reporter.print_report()
```

## Error Types

### 1. LexerError

Used during lexical analysis for:
- Invalid characters
- Unterminated strings
- Malformed numbers
- Invalid escape sequences

**Factory Methods:**
```python
LexerError.invalid_character(char, span)
LexerError.unterminated_string(span)
LexerError.invalid_escape_sequence(seq, span)
LexerError.invalid_number(text, span)
```

**Error Codes:** `L001` - `L004`

### 2. ParseError

Used during parsing for:
- Unexpected tokens
- Missing delimiters
- Invalid syntax
- Unexpected EOF

**Factory Methods:**
```python
ParseError.unexpected_token(expected, found, span)
ParseError.missing_delimiter(delimiter, span)
ParseError.invalid_syntax(description, span)
ParseError.unexpected_eof(expected, span)
```

**Error Codes:** `P001` - `P004`

### 3. TypeError

Used during type checking for:
- Type mismatches
- Unknown types
- Invalid operations
- Incompatible types

**Factory Methods:**
```python
TypeError.type_mismatch(expected, found, span)
TypeError.unknown_type(type_name, span)
TypeError.invalid_operation(op, type1, type2, span)
TypeError.incompatible_types(type1, type2, context, span)
```

**Error Codes:** `T001` - `T004`

### 4. OwnershipError

Used for ownership and borrowing violations:
- Use after move
- Double free
- Invalid borrows
- Mutable borrow conflicts

**Factory Methods:**
```python
OwnershipError.use_after_move(var_name, span, moved_at)
OwnershipError.double_free(var_name, span, first_free)
OwnershipError.invalid_borrow(var_name, reason, span)
OwnershipError.mutable_borrow_conflict(var_name, span, existing_borrow)
```

**Error Codes:** `O001` - `O004`

### 5. NameError

Used for name resolution issues:
- Undefined variables
- Duplicate definitions
- Undefined functions
- Undefined types

**Factory Methods:**
```python
NameError.undefined_variable(var_name, span)
NameError.duplicate_definition(name, span, first_def)
NameError.undefined_function(func_name, span)
NameError.undefined_type(type_name, span)
```

**Error Codes:** `N001` - `N004`

### 6. CompilerWarning

Used for non-fatal issues:
- Unused variables
- Unreachable code
- Deprecated features

**Factory Methods:**
```python
CompilerWarning.unused_variable(var_name, span)
CompilerWarning.unreachable_code(span)
CompilerWarning.deprecated_feature(feature, replacement, span)
```

**Warning Codes:** `W001` - `W003`

## SourceSpan

Track the exact location of errors in source code:

```python
span = SourceSpan(
    file="example.bh",           # Source file path
    line=10,                      # Starting line (1-indexed)
    column=5,                     # Starting column (1-indexed)
    end_line=10,                  # Ending line (optional)
    end_column=12,                # Ending column (optional)
    source_line='let x: i32 = "hello";'  # Actual source line (optional)
)
```

The `source_line` is used to display the code context with a caret pointing to the error.

## ErrorReporter

The `ErrorReporter` class collects and formats all errors and warnings:

### Key Methods

```python
# Create reporter (with or without colors)
reporter = ErrorReporter(use_color=True)

# Add errors and warnings
reporter.add_error(error)
reporter.add_warning(warning)

# Check status
has_errors = reporter.has_errors()
has_warnings = reporter.has_warnings()
error_count = reporter.error_count()
warning_count = reporter.warning_count()

# Get formatted output
report_text = reporter.report()
reporter.print_report()

# Get all diagnostics
all_diagnostics = reporter.get_all_diagnostics()

# Clear all diagnostics
reporter.clear()
```

## Example Output

### Error Example

```
error[T001]: type mismatch: expected 'i32', found 'str'
  --> example.bh:10:9

  10 | let x: i32 = "hello";
              ^^^^^^^^

```

### Warning Example

```
warning[W001]: unused variable: 'temp'
  --> example.bh:5:9

  5 |     let temp = 42;
           ^

  note: prefix with '_' to suppress this warning
```

### Multiple Errors with Summary

```
error[T001]: type mismatch: expected 'i32', found 'str'
  --> mixed.bh:10:9

  10 | let x: i32 = "invalid";
              ^^^^^^^^

error[N001]: undefined variable: 'unknown'
  --> mixed.bh:20:5

  20 |     println(unknown);
          ^^^^^^^^^^^

  note: make sure the variable is declared before use

warning[W001]: unused variable: 'temp'
  --> mixed.bh:5:9

  5 |     let temp = 42;
           ^

  note: prefix with '_' to suppress this warning

2 errors, 1 warning generated
```

## Integration with Compiler Phases

### Lexer Integration

```python
def tokenize(source_code: str, filename: str) -> tuple[list, ErrorReporter]:
    reporter = ErrorReporter()
    tokens = []

    for char in source_code:
        if is_invalid(char):
            span = create_span(filename, current_line, current_col)
            error = LexerError.invalid_character(char, span)
            reporter.add_error(error)

    return tokens, reporter
```

### Parser Integration

```python
def parse(tokens: list, reporter: ErrorReporter) -> AST:
    try:
        ast = build_ast(tokens)
        return ast
    except UnexpectedToken as e:
        error = ParseError.unexpected_token(e.expected, e.found, e.span)
        reporter.add_error(error)
        # Continue parsing with recovery...
```

### Type Checker Integration

```python
def type_check(ast: AST, reporter: ErrorReporter):
    for node in ast.nodes:
        expected_type = infer_type(node)
        actual_type = node.type

        if expected_type != actual_type:
            error = TypeError.type_mismatch(
                expected_type, actual_type, node.span
            )
            reporter.add_error(error)
```

## Customization

### Disabling Colors

For environments without terminal color support:

```python
reporter = ErrorReporter(use_color=False)
```

### Custom Error Types

Create custom error types by extending `CompilerError`:

```python
class OptimizationError(CompilerError):
    @staticmethod
    def failed_optimization(reason: str, span: SourceSpan) -> 'OptimizationError':
        return OptimizationError(
            message=f"optimization failed: {reason}",
            span=span,
            error_code="OPT001"
        )
```

## Best Practices

1. **Always provide source spans** when available for better error messages
2. **Use factory methods** instead of creating errors directly
3. **Add helpful notes** to guide users toward fixes
4. **Collect all errors** before stopping compilation (don't fail on first error)
5. **Use warnings** for issues that don't prevent compilation
6. **Provide error codes** for documentation lookup
7. **Include context** from previous locations (e.g., where a variable was first defined)

## Testing

Run the test suite to see examples of all error types:

```bash
cd compiler
python3 test_errors.py
```

This will display formatted examples of all error types with colorized output.

## Error Code Reference

### Lexer Errors (L001-L099)
- `L001`: Invalid character
- `L002`: Unterminated string
- `L003`: Invalid escape sequence
- `L004`: Invalid number

### Parser Errors (P001-P099)
- `P001`: Unexpected token
- `P002`: Missing delimiter
- `P003`: Invalid syntax
- `P004`: Unexpected EOF

### Type Errors (T001-T099)
- `T001`: Type mismatch
- `T002`: Unknown type
- `T003`: Invalid operation
- `T004`: Incompatible types

### Ownership Errors (O001-O099)
- `O001`: Use after move
- `O002`: Double free
- `O003`: Invalid borrow
- `O004`: Mutable borrow conflict

### Name Errors (N001-N099)
- `N001`: Undefined variable
- `N002`: Duplicate definition
- `N003`: Undefined function
- `N004`: Undefined type

### Warnings (W001-W099)
- `W001`: Unused variable
- `W002`: Unreachable code
- `W003`: Deprecated feature

## Future Enhancements

Potential improvements to consider:

- [ ] Error recovery suggestions (e.g., "did you mean 'foo'?")
- [ ] Multi-line error spans
- [ ] Error suppression via pragmas
- [ ] JSON output for IDE integration
- [ ] Localization support
- [ ] Configurable error levels
- [ ] Performance tracking
- [ ] Error statistics
